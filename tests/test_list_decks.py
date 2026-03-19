import json

import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


@pytest.mark.integration
def test_list_decks_sorted_output(repo):
    repo(
        decks={
            "zebra": {"id": "z1", "file": "card_library/decks/zebra.txt"},
            "alpha": {"id": "a1", "file": "card_library/decks/alpha.txt"},
            "middle": {"id": "m1", "file": "card_library/decks/middle.txt"},
        }
    )
    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    output = result.output
    # Header row is present
    assert "Alias" in output
    assert "File" in output
    # All decks appear in output
    assert "alpha" in output
    assert "middle" in output
    assert "zebra" in output
    assert "card_library/decks/alpha.txt" in output
    assert "card_library/decks/middle.txt" in output
    assert "card_library/decks/zebra.txt" in output
    # Sorted: alpha before middle before zebra
    assert output.index("alpha") < output.index("middle") < output.index("zebra")


@pytest.mark.integration
def test_list_decks_empty_decks(repo):
    repo(decks={})
    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    # With empty decks, list_decks returns early — no table content
    assert "Alias" not in result.output


@pytest.mark.integration
def test_list_decks_missing_config_creates_default(tmp_path, monkeypatch):
    """When no config.json exists, load_config creates a default and list-decks prints it."""
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    assert "example_deck" in result.output
    # The default config file should have been created
    assert (tmp_path / "config.json").exists()


@pytest.mark.integration
def test_list_decks_custom_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom_config = tmp_path / "custom.json"
    config = {
        "binder_id": "test",
        "decks": {
            "my_deck": {"id": "x1", "file": "card_library/decks/my_deck.txt"},
        },
        "purchased_file": "card_library/purchased.txt",
    }
    custom_config.write_text(json.dumps(config))
    result = CliRunner().invoke(cli, ["list-decks", "--config-file", str(custom_config)])
    assert result.exit_code == 0
    assert "my_deck" in result.output
    assert "card_library/decks/my_deck.txt" in result.output
