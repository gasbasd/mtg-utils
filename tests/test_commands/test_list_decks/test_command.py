import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


@pytest.mark.integration
def test_list_decks_shows_card_contents(repo):
    """list-decks now shows card contents for each deck."""
    repo(
        decks={
            "test_deck": {"id": "t1", "file": "card_library/decks/test_deck.txt"},
        }
    )

    # Create deck file with content
    with open("card_library/decks/test_deck.txt", "w") as f:
        f.write("1 Forest\n1 Island\n")

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    # Should show rule header
    assert "Configured decks with card contents" in result.output
    # Should show deck name with card count
    assert "test_deck (2 cards)" in result.output
    # Should show card contents
    assert "Forest" in result.output
    assert "Island" in result.output


@pytest.mark.integration
def test_list_decks_empty_deck(repo):
    """Empty decks show appropriate message."""
    repo(
        decks={
            "empty_deck": {"id": "e1", "file": "card_library/decks/empty_deck.txt"},
        }
    )

    # Create empty deck file
    with open("card_library/decks/empty_deck.txt", "w") as f:
        f.write("")

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    # Should show empty deck message
    assert "empty_deck (0 cards)" in result.output or "(empty deck)" in result.output


@pytest.mark.integration
def test_list_decks_no_config_file(repo):
    """Test with no decks configured."""
    repo(decks={})

    result = CliRunner().invoke(cli, ["list-decks"])
    assert result.exit_code == 0
    assert "Configured decks with card contents" not in result.output
