import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


def _run(library, deck_lists=None, extra_args=None):
    deck_lists = deck_lists or []
    runner = CliRunner()
    with patch("mtg_utils.commands.update_card_library.command.get_library", return_value=library):
        with patch(
            "mtg_utils.commands.update_card_library.command.get_deck_list",
            side_effect=deck_lists if deck_lists else [[]],
        ):
            return runner.invoke(cli, ["update-card-library"] + (extra_args or []))


# ---------------------------------------------------------------------------
# Owned cards
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_writes_owned_cards(repo, tmp_path):
    repo()

    result = _run(library=["3 Island", "2 Forest"])

    assert result.exit_code == 0
    owned = (tmp_path / "card_library" / "owned_cards.txt").read_text()
    assert "3 Island" in owned
    assert "2 Forest" in owned


# ---------------------------------------------------------------------------
# Available cards
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_available_subtracts_deck(repo, tmp_path):
    repo(decks={"my_deck": {"file": "card_library/decks/my_deck.txt", "id": "d1"}})

    result = _run(library=["3 Island", "2 Forest"], deck_lists=[["1 Island"]])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # 3 owned - 1 in deck = 2
    assert "2 Forest" in available  # untouched


@pytest.mark.integration
def test_same_card_in_multiple_decks(repo, tmp_path):
    """Second deck using the same card increments used_cards (the += branch)."""
    repo(
        decks={
            "alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"},
            "beta": {"file": "card_library/decks/beta.txt", "id": "b1"},
        },
    )

    result = _run(library=["4 Island"], deck_lists=[["1 Island"], ["1 Island"]])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # 4 owned - 1 alpha - 1 beta = 2


# ---------------------------------------------------------------------------
# Purchased cards
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_creates_purchased_file_when_absent(repo, tmp_path):
    repo()

    result = _run(library=["1 Island"])

    assert result.exit_code == 0
    assert (tmp_path / "card_library" / "purchased.txt").exists()


@pytest.mark.integration
def test_purchased_cards_written_to_formatted_file(repo, tmp_path):
    repo()
    (tmp_path / "card_library" / "purchased.txt").write_text("Island\nIsland\n")

    result = _run(library=["2 Island"])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available
    purchased_formatted = (tmp_path / "card_library" / "purchased_formatted.txt").read_text()
    assert "2 Island" in purchased_formatted


@pytest.mark.integration
def test_purchased_card_not_in_library(repo, tmp_path):
    """Purchased card not in owned library is written to purchased_formatted.txt but not available_cards.txt."""
    repo()
    (tmp_path / "card_library" / "purchased.txt").write_text("Forest\n")

    result = _run(library=["2 Island"])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "Forest" not in available
    assert "2 Island" in available
    purchased_formatted = (tmp_path / "card_library" / "purchased_formatted.txt").read_text()
    assert "1 Forest" in purchased_formatted


# ---------------------------------------------------------------------------
# Deck sync
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_deck_file_written(repo, tmp_path):
    repo(decks={"alpha": {"file": "card_library/decks/alpha.txt", "id": "d1"}})

    result = _run(library=["2 Lightning Bolt"], deck_lists=[["1 Lightning Bolt"]])

    assert result.exit_code == 0
    deck_content = (tmp_path / "card_library" / "decks" / "alpha.txt").read_text()
    assert "1 Lightning Bolt" in deck_content


@pytest.mark.integration
def test_deck_retrieval_fails_marks_failed(repo):
    """Else-branch in command: empty deck list → DeckFetchResult with ok=False, no file written."""
    repo(decks={"broken": {"file": "card_library/decks/broken.txt", "id": "d1"}})

    result = _run(library=["1 Island"], deck_lists=[[]])

    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Unavailable cards warnings
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_unavailable_with_sharing_and_already_used(repo):
    """'sharing:' and 'already used:' both appear in the warning message."""
    repo(
        decks={
            "base": {"file": "card_library/decks/base.txt", "id": "base-id"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["base"],
            },
        },
    )

    result = _run(
        library=[],  # no owned cards
        deck_lists=[["1 Lightning Bolt"], ["3 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "sharing" in result.output
    assert "already used" in result.output


@pytest.mark.integration
def test_purchased_formatted_file_missing_is_handled(repo):
    """purchased_formatted_file key set but file absent → FileNotFoundError silently ignored."""
    repo(
        decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}},
        purchased_formatted_file="card_library/purchased_formatted.txt",
    )
    # purchased_formatted.txt intentionally NOT created

    result = _run(library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output


# ---------------------------------------------------------------------------
# shared_decks
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_shared_decks_no_extra_consumption(repo, tmp_path):
    repo(
        decks={
            "base": {"file": "card_library/decks/base.txt", "id": "base-id"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["base"],
            },
        },
    )

    result = _run(
        library=["2 Lightning Bolt"],
        deck_lists=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "1 Lightning Bolt" in available


@pytest.mark.integration
def test_shared_deck_missing_reference_warns(repo):
    repo(
        decks={
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["nonexistent"],
            },
        },
    )

    result = _run(library=["1 Island"], deck_lists=[["1 Island"]])

    assert result.exit_code == 0
    assert "nonexistent" in result.output


@pytest.mark.integration
def test_multiple_shared_decks_one_missing(repo):
    """'nonexistent' shared deck hits the `continue` branch in the render loop."""
    repo(
        decks={
            "alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "c1",
                "shared_decks": ["alpha", "nonexistent"],
            },
        },
    )

    result = _run(
        library=["2 Lightning Bolt"],
        deck_lists=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "child" in result.output


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_custom_config_file(repo, tmp_path):
    repo()
    cfg_path = tmp_path / "custom.json"
    cfg_path.write_text(
        json.dumps(
            {
                "binder_id": "b",
                "decks": {},
                "purchased_file": "card_library/purchased.txt",
            }
        )
    )

    result = _run(library=["1 Forest"], extra_args=["--config-file", str(cfg_path)])

    assert result.exit_code == 0
    assert (tmp_path / "card_library" / "owned_cards.txt").exists()
