import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


@pytest.fixture
def setup_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _setup(available_cards, deck_cards_by_name=None):
        card_lib = tmp_path / "card_library"
        card_lib.mkdir(exist_ok=True)
        available_txt = "\n".join(available_cards) + ("\n" if available_cards else "")
        (card_lib / "available_cards.txt").write_text(available_txt)

        decks_cfg = {}
        if deck_cards_by_name:
            (card_lib / "decks").mkdir(exist_ok=True)
            for name, cards in deck_cards_by_name.items():
                deck_file = card_lib / "decks" / f"{name}.txt"
                deck_file.write_text("\n".join(cards) + "\n")
                decks_cfg[name] = {"file": str(deck_file), "id": "fake"}

        config = {
            "binder_id": "x",
            "decks": decks_cfg,
            "purchased_file": "card_library/purchased.txt",
            "purchased_formatted_file": "card_library/purchased_formatted.txt",
        }
        (tmp_path / "config.json").write_text(json.dumps(config))
        return tmp_path

    return _setup


# --- validation errors (no files needed) ---


@pytest.mark.integration
def test_check_missing_no_options():
    result = CliRunner().invoke(cli, ["check-missing-cards"])
    assert result.exit_code == 1
    assert "Error: You must provide either" in result.output


@pytest.mark.integration
def test_check_missing_both_options(tmp_path):
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("1 Island\n")
    result = CliRunner().invoke(
        cli,
        [
            "check-missing-cards",
            "--deck-file",
            str(deck_file),
            "--moxfield-id",
            "fake-id",
        ],
    )
    assert result.exit_code == 1
    assert "Error: Please provide only one" in result.output


@pytest.mark.integration
def test_check_missing_moxfield_id_not_found():
    with patch("mtg_utils.commands.check_missing_cards.command.get_deck_list", return_value=[]):
        result = CliRunner().invoke(cli, ["check-missing-cards", "--moxfield-id", "bad-id"])
    assert result.exit_code == 1
    assert "Could not retrieve deck" in result.output


# --- happy path: all cards available ---


@pytest.mark.integration
def test_check_missing_all_available(setup_repo):
    tmp_path = setup_repo(available_cards=["4 Island", "3 Forest"])
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("2 Island\n1 Forest\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Total cards in deck: 3" in result.output
    assert "All cards available" in result.output


# --- some cards completely missing ---


@pytest.mark.integration
def test_check_missing_some_missing(setup_repo):
    tmp_path = setup_repo(available_cards=["1 Island"])
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("2 Island\n1 Lightning Bolt\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Missing:" in result.output
    assert "Lightning Bolt" in result.output
    # "All cards available" must NOT appear
    assert "All cards available" not in result.output


# --- cards available in other configured decks ---


@pytest.mark.integration
def test_check_missing_cards_in_other_decks(setup_repo):
    tmp_path = setup_repo(
        available_cards=[],
        deck_cards_by_name={"other_deck": ["1 Lightning Bolt"]},
    )
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Lightning Bolt\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "In other decks" in result.output
    assert "Lightning Bolt" in result.output
    assert "other_deck" in result.output
    # Completely missing section must not appear (card is sourced from other deck)
    assert "All cards available" in result.output


# --- partially sourced from other decks, remainder still missing ---


@pytest.mark.integration
def test_check_missing_partial_from_other_deck(setup_repo):
    tmp_path = setup_repo(
        available_cards=[],
        deck_cards_by_name={"other_deck": ["1 Lightning Bolt"]},
    )
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("3 Lightning Bolt\n")  # need 3, other deck only has 1

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Missing:" in result.output
    assert "In other decks" in result.output
    assert "other_deck" in result.output


@pytest.mark.integration
def test_check_missing_no_deck_column_when_no_other_decks(setup_repo):
    """When no configured decks exist, the Missing panel still renders correctly."""
    tmp_path = setup_repo(available_cards=[])  # no deck_cards_by_name → no configured decks
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Lightning Bolt\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Missing:" in result.output
    assert "Lightning Bolt" in result.output


# --- via --moxfield-id (mocked) ---


@pytest.mark.integration
def test_check_missing_via_moxfield_id(setup_repo):
    setup_repo(available_cards=["2 Island"])

    with patch("mtg_utils.commands.check_missing_cards.command.get_deck_list", return_value=["1 Island"]):
        result = CliRunner().invoke(cli, ["check-missing-cards", "--moxfield-id", "deck-id"])

    assert result.exit_code == 0
    assert "Total cards in deck: 1" in result.output


# --- purchased marker (*) ---


@pytest.mark.integration
def test_check_missing_purchased_marker_not_shown_when_available(setup_repo):
    """Cards that are already available do NOT show * even if also in purchased file."""
    tmp_path = setup_repo(available_cards=["2 Island"])
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Island\n")
    (tmp_path / "card_library" / "purchased_formatted.txt").write_text("1 Island\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Island" in result.output
    assert "*" not in result.output


@pytest.mark.integration
def test_check_missing_purchased_marker_in_deck_breakdown(setup_repo):
    """Cards in the purchased file show * in the per-deck breakdown panel."""
    tmp_path = setup_repo(
        available_cards=[],
        deck_cards_by_name={"other_deck": ["1 Lightning Bolt"]},
    )
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("3 Lightning Bolt\n")
    (tmp_path / "card_library" / "purchased_formatted.txt").write_text("1 Lightning Bolt\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Lightning Bolt" in result.output
    assert "*" in result.output


@pytest.mark.integration
def test_check_missing_no_marker_when_not_purchased(setup_repo):
    """No * marker appears when the purchased file does not exist."""
    tmp_path = setup_repo(available_cards=["2 Island"])
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Island\n")
    # purchased.txt is not created — FileNotFoundError fallback, no markers expected

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Island" in result.output
    assert "*" not in result.output
    assert "All cards available" in result.output


@pytest.mark.integration
def test_check_missing_purchased_marker_shown_when_only_from_purchased(setup_repo):
    """Card absent from available_cards.txt but present in purchased shows * in Available panel."""
    tmp_path = setup_repo(available_cards=[])  # not in owned cards at all
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Syphon Mind\n")
    (tmp_path / "card_library" / "purchased_formatted.txt").write_text("1 Syphon Mind\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Syphon Mind" in result.output
    assert "*" in result.output


@pytest.mark.integration
def test_check_missing_deck_breakdown_multiple_columns(setup_repo):
    """Per-deck breakdown panels are rendered in rows of up to 3 columns."""
    tmp_path = setup_repo(
        available_cards=[],
        deck_cards_by_name={
            "deck_a": ["1 Lightning Bolt"],
            "deck_b": ["1 Island"],
            "deck_c": ["1 Forest"],
            "deck_d": ["1 Swamp"],
        },
    )
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Lightning Bolt\n1 Island\n1 Forest\n1 Swamp\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "deck_a" in result.output
    assert "deck_b" in result.output
    assert "deck_c" in result.output
    assert "deck_d" in result.output


@pytest.mark.integration
def test_check_missing_deck_breakdown_unequal_row_height(setup_repo):
    """Two decks in the same per-deck breakdown row with unequal card counts exercise
    the row_height = max(cards per deck) + 2 equal-height fix.

    deck_a supplies 1 card; deck_b supplies 2 cards → max(1, 2) + 2 = 4.
    Both panel titles must appear, confirming neither panel was dropped.
    """
    tmp_path = setup_repo(
        available_cards=[],
        deck_cards_by_name={
            "deck_a": ["1 Lightning Bolt"],
            "deck_b": ["1 Island", "1 Forest"],
        },
    )
    deck_file = tmp_path / "target.txt"
    # Lightning Bolt only in deck_a; Island and Forest only in deck_b
    deck_file.write_text("1 Lightning Bolt\n1 Island\n1 Forest\n")

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    # Both per-deck breakdown panels must have rendered
    assert "deck_a" in result.output
    assert "deck_b" in result.output
