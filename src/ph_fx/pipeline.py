"""
Pipeline CLI entry point.

Commands:
  ph-fx ingest       — fetch from BSP + Frankfurter → PostgreSQL → dbt
  ph-fx transform    — run dbt models only
  ph-fx status       — print row counts + latest rates
  ph-fx reset        — drop raw schema (destructive)
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ph_fx.config import settings
from ph_fx.ingestion.bsp_historical import fetch_cross_rates, fetch_monthly_usdphp
from ph_fx.ingestion.bsp_rerb import fetch_daily_rate
from ph_fx.ingestion.frankfurter import fetch_latest_usdphp
from ph_fx.loader import ensure_schema, row_counts, upsert_cross_rates, upsert_fx_rates

app    = typer.Typer(name="ph-fx", help="PH FX Dashboard Pipeline", no_args_is_help=True)
console = Console()
logger  = logging.getLogger(__name__)

DBT_DIR = Path(__file__).parent.parent.parent.parent / "transforms"


@app.command()
def ingest(
    source: str = typer.Option("all", help="all | bsp | frankfurter"),
    skip_dbt: bool = typer.Option(False, help="Skip dbt transforms after ingest"),
) -> None:
    """Fetch FX rates from BSP (+ Frankfurter fallback) → PostgreSQL → dbt."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_schema()
    total = 0

    if source in ("all", "bsp"):
        console.print("[bold blue]Fetching BSP daily rate...[/bold blue]")
        daily = fetch_daily_rate()
        if daily:
            total += upsert_fx_rates([daily])
            console.print(f"  ✓ Daily rate: {daily.rate_date} — ₱{daily.rate:.4f}")
        else:
            console.print("  ⚠ BSP daily unavailable — trying Frankfurter fallback...")
            fallback = fetch_latest_usdphp()
            if fallback:
                total += upsert_fx_rates([fallback])
                console.print(f"  ✓ Fallback rate: {fallback.rate_date} — ₱{fallback.rate:.4f}")

        console.print("[bold blue]Fetching BSP historical monthly (Table 12)...[/bold blue]")
        monthly = fetch_monthly_usdphp(start_year=settings.start_year)
        total += upsert_fx_rates(monthly)
        console.print(f"  ✓ {len(monthly)} monthly records upserted.")

        console.print("[bold blue]Fetching BSP cross rates (Table 13)...[/bold blue]")
        cross = fetch_cross_rates()
        total += upsert_cross_rates(cross)
        console.print(f"  ✓ {len(cross)} cross rate records upserted.")

    if source in ("all", "frankfurter"):
        if source == "frankfurter":
            console.print("[bold blue]Fetching Frankfurter fallback...[/bold blue]")
            fallback = fetch_latest_usdphp()
            if fallback:
                total += upsert_fx_rates([fallback])
                console.print(f"  ✓ {fallback.rate_date} — ₱{fallback.rate:.4f}")

    console.print(f"\n[bold green]Ingest complete — {total} records upserted.[/bold green]")

    if not skip_dbt:
        transform()


@app.command()
def transform(target: str = typer.Option("dev", help="dbt target profile")) -> None:
    """Run dbt models to rebuild mart tables."""
    console.print("[bold blue]Running dbt...[/bold blue]")
    result = subprocess.run(
        [sys.executable, "-m", "dbt", "run", "--profiles-dir", str(DBT_DIR),
         "--target", target],
        cwd=DBT_DIR,
    )
    if result.returncode != 0:
        console.print("[bold red]dbt run failed.[/bold red]")
        raise typer.Exit(1)
    console.print("[bold green]dbt complete.[/bold green]")


@app.command()
def status() -> None:
    """Show warehouse row counts and latest rates."""
    counts = row_counts()
    t = Table(title="ph-fx-dashboard — Warehouse Status")
    t.add_column("Table", style="cyan")
    t.add_column("Rows", justify="right", style="green")
    for table, count in counts.items():
        t.add_row(table, f"{count:,}")
    console.print(t)


@app.command()
def reset(confirm: bool = typer.Option(False, "--confirm", help="Required to proceed")) -> None:
    """Drop raw schema — destructive, requires --confirm."""
    if not confirm:
        console.print("[red]Pass --confirm to drop the raw schema.[/red]")
        raise typer.Exit(1)
    import psycopg2
    from ph_fx.loader import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS raw CASCADE;")
        conn.commit()
    console.print("[bold red]Raw schema dropped.[/bold red]")


if __name__ == "__main__":
    app()
