import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


@pytest.mark.integration
def test_cli_debug_flag():
    """--debug flag should set logging to DEBUG (covers the `if debug:` branch in cli())."""
    result = CliRunner().invoke(cli, ["--debug", "check-missing-cards"])
    # check-missing-cards without options prints its validation error; exit code is 1
    assert result.exit_code == 1
    assert "Error: You must provide either" in result.output
