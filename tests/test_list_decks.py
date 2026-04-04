import json
import os

import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


@pytest.mark.integration
def test_list_decks_sorted_output(repo):
    """Test list-decks shows multiple decks with card contents and separation."""
    repo(
        decks={
            "zebra": {"id": "z1", "file": "card_library/decks/zebra.txt"},
            "alpha": {"id": "a1", "file": "card_library/decks/alpha.txt"},
            "middle": {"id": "m1", "file": "card_library/decks/middle.txt"},
        }
    )
    # Create deck files with some card content
    decks_dir = "card_library/decks"
    with open(os.path.join(decks_dir, "alpha.txt"), "w") as f:
        f.write("1 Snow-Covered Forest\n1 Snow-Covered Island\n1 Forest\n1 Island\n")
    with open(os.path.join(decks_dir, "middle.txt"), "w") as f:
        f.write("1 Forest\n1 Island\n1 Plains\n1 Mountain\n")
    with open(os.path.join(decks_dir, "zebra.txt"), "w") as f:
        f.write("1 Forest\n1 Island\n1 Swamp\n1 Plains\n")

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    output = result.output
    # Rule header is present
    assert "Configured decks with card contents" in output
    # All decks appear in output with their card counts
    assert "alpha (4 cards)" in output
    assert "middle (4 cards)" in output
    assert "zebra (4 cards)" in output
    # Sorted: alpha before middle before zebra
    assert output.index("alpha") < output.index("middle") < output.index("zebra")
    # Deck contents are shown
    assert "Snow-Covered Forest" in output
    assert "Snow-Covered Island" in output
    # Check that empty lines separate decks (line 38-39 coverage)
    assert "\n\n" in output  # Empty line between deck outputs


@pytest.mark.integration
def test_list_decks_empty_decks(repo):
    repo(decks={})
    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    # With empty decks, list_decks returns early
    assert "Configured decks with card contents" not in result.output


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

    # Create deck file with content
    decks_dir = "card_library/decks"
    os.makedirs(decks_dir, exist_ok=True)
    with open(os.path.join(decks_dir, "my_deck.txt"), "w") as f:
        f.write("1 Snow-Covered Forest\n1 Snow-Covered Island\n1 Forest\n1 Island\n")

    result = CliRunner().invoke(cli, ["list-decks", "--config-file", str(custom_config)])
    assert result.exit_code == 0
    assert "my_deck (4 cards)" in result.output
    # Deck contents are shown
    assert "Snow-Covered Forest" in result.output
    assert "Snow-Covered Island" in result.output


@pytest.mark.integration
def test_list_decks_panel_title(repo):
    """Rule 'Configured decks with card contents' appears for a 3-deck config."""
    repo(
        decks={
            "alpha": {"id": "a1", "file": "card_library/decks/alpha.txt"},
            "beta": {"id": "b1", "file": "card_library/decks/beta.txt"},
            "gamma": {"id": "g1", "file": "card_library/decks/gamma.txt"},
        }
    )
    # Create deck files with content
    decks_dir = "card_library/decks"
    for deck_name in ["alpha", "beta", "gamma"]:
        with open(os.path.join(decks_dir, f"{deck_name}.txt"), "w") as f:
            f.write("1 Forest\n1 Island\n")

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    assert "Configured decks with card contents" in result.output


@pytest.mark.integration
def test_list_decks_panel_title_single(repo):
    """Rule 'Configured decks with card contents' appears for a single-deck config."""
    repo(decks={"only_one": {"id": "x1", "file": "card_library/decks/only_one.txt"}})

    # Create deck file with content
    decks_dir = "card_library/decks"
    with open(os.path.join(decks_dir, "only_one.txt"), "w") as f:
        f.write("1 Forest\n1 Island\n")

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    assert "Configured decks with card contents" in result.output
