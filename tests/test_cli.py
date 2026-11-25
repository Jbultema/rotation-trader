from typer.testing import CliRunner

from rotation_trader.cli import app


def test_cli_exposes_research_operations_and_dashboard_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "research" in result.output
    assert "audit" in result.output
    assert "record-shadow" in result.output
    assert "dashboard" in result.output
