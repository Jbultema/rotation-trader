from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from rotation_trader.audit import audit_research_run
from rotation_trader.config import load_config
from rotation_trader.data import (
    download_price_snapshot,
    latest_price_manifest,
    load_price_snapshot,
)
from rotation_trader.research import run_research
from rotation_trader.shadow import record_shadow_decision

app = typer.Typer(
    no_args_is_help=True,
    help="Research-only sector leadership and transition decision support.",
)


@app.command("fetch-data")
def fetch_data(
    config_path: Annotated[Path, typer.Option("--config")] = Path("config/default.toml"),
    output_dir: Annotated[Path, typer.Option("--output")] = Path("data/raw/prices"),
) -> None:
    """Download a completed-session, hashed public market-data snapshot."""
    config = load_config(config_path)
    snapshot = download_price_snapshot(config.data, output_dir)
    typer.echo(
        f"Locked {snapshot.audit.latest_session} price snapshot at {snapshot.manifest_path}; "
        "no order was placed."
    )


@app.command("research")
def research(
    config_path: Annotated[Path, typer.Option("--config")] = Path("config/default.toml"),
    price_manifest: Annotated[
        Path | None,
        typer.Option("--prices", help="Hashed price manifest; defaults to latest."),
    ] = None,
    output_dir: Annotated[Path, typer.Option("--output")] = Path("reports"),
) -> None:
    """Run the frozen search, seal selection, then open holdout evidence once."""
    config = load_config(config_path)
    manifest = price_manifest or latest_price_manifest(Path("data/raw/prices"))
    result = run_research(
        load_price_snapshot(manifest),
        config,
        output_dir,
        price_manifest_path=manifest,
        progress=typer.echo,
    )
    typer.echo(
        f"Research complete: {result.variants_tested} variants; "
        f"selected={result.selected_variant_id}; promoted={result.promoted}; "
        f"artifacts={result.run_dir}; no order was placed."
    )


@app.command("run")
def run(
    config_path: Annotated[Path, typer.Option("--config")] = Path("config/default.toml"),
) -> None:
    """Refresh completed data and execute the full frozen research protocol."""
    config = load_config(config_path)
    snapshot = download_price_snapshot(config.data, Path("data/raw/prices"))
    result = run_research(
        load_price_snapshot(snapshot.manifest_path),
        config,
        Path("reports"),
        price_manifest_path=snapshot.manifest_path,
        progress=typer.echo,
    )
    shadow = record_shadow_decision(result.latest_dir, Path("data/shadow/decisions.jsonl"))
    typer.echo(
        f"Rotation Trader completed through {snapshot.audit.latest_session}: "
        f"selected={result.selected_variant_id}; promoted={result.promoted}; "
        f"shadow_record={shadow['record_id']}; no order was placed."
    )


@app.command("show")
def show(
    report_dir: Annotated[Path, typer.Option("--reports")] = Path("reports/latest"),
) -> None:
    """Show the latest research status and human-review allocation."""
    payload = json.loads((report_dir / "research_summary.json").read_text(encoding="utf-8"))
    decision = payload.get("latest_decision")
    typer.echo(f"Promotion status: {payload['promotion_status']}")
    typer.echo(f"Selected variant: {payload.get('selected_variant_id')}")
    if isinstance(decision, dict):
        typer.echo(f"As of close: {decision['as_of_close']}")
        typer.echo(f"Leadership state: {decision['leadership_state']}")
        typer.echo(f"Targets: {json.dumps(decision['target_weights'], sort_keys=True)}")
        typer.echo(f"Cash: {decision['cash_weight']:.1%}")
    typer.echo("Research only; human execution required; no action is authorized.")


@app.command("audit")
def audit(
    report_dir: Annotated[Path, typer.Option("--reports")] = Path("reports/latest"),
) -> None:
    """Verify hashes and the sealed pre-holdout selection record."""
    result = audit_research_run(report_dir)
    typer.echo(
        f"Audit {result.status}: passed={result.passed}; "
        f"artifacts={result.artifacts_checked}; selected={result.selected_variant_id}; "
        f"promoted={result.promoted}."
    )
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("record-shadow")
def record_shadow(
    report_dir: Annotated[Path, typer.Option("--reports")] = Path("reports/latest"),
    journal: Annotated[Path, typer.Option("--journal")] = Path(
        "data/shadow/decisions.jsonl"
    ),
) -> None:
    """Append one idempotent, unactionable prospective shadow decision."""
    record = record_shadow_decision(report_dir, journal)
    typer.echo(
        f"Shadow record {record['record_id']} is locked through {record['as_of_close']}; "
        "no action is authorized."
    )


@app.command("dashboard")
def dashboard(
    port: Annotated[int, typer.Option("--port")] = 8503,
) -> None:
    """Run the local research dashboard."""
    module_path = Path(__file__).with_name("dashboard.py")
    raise typer.Exit(
        code=subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(module_path),
                "--server.headless=true",
                f"--server.port={port}",
            ]
        )
    )
