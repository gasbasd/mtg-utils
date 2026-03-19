import json
from unittest.mock import patch
from click.testing import CliRunner
from mtg_utils.main import cli


def _setup(tmp_path, available_cards, deck_cards_by_name=None):
    """Create card_library structure and config.json under tmp_path."""
    card_lib = tmp_path / "card_library"
    card_lib.mkdir()
    available_txt = "\n".join(available_cards) + ("\n" if available_cards else "")
    (card_lib / "available_cards.txt").write_text(available_txt)

    decks_cfg = {}
    if deck_cards_by_name:
        (card_lib / "decks").mkdir()
        for name, cards in deck_cards_by_name.items():
            deck_file = card_lib / "decks" / f"{name}.txt"
            deck_file.write_text("\n".join(cards) + "\n")
            decks_cfg[name] = {"file": str(deck_file), "id": "fake"}

    config = {
        "binder_id": "x",
        "decks": decks_cfg,
        "purchased_file": "card_library/purchased.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))


# --- validation errors (no files needed) ---

def test_check_missing_no_options():
    result = CliRunner().invoke(cli, ["check-missing-cards"])
    assert result.exit_code == 0
    assert "Error: You must provide either" in result.output


def test_check_missing_both_options(tmp_path):
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("1 Island\n")
    result = CliRunner().invoke(cli, [
        "check-missing-cards",
        "--deck-file", str(deck_file),
        "--moxfield-id", "fake-id",
    ])
    assert result.exit_code == 0
    assert "Error: Please provide only one" in result.output


def test_check_missing_moxfield_id_not_found():
    with patch("mtg_utils.commands.check_missing_cards.get_deck_list", return_value=[]):
        result = CliRunner().invoke(cli, ["check-missing-cards", "--moxfield-id", "bad-id"])
    assert result.exit_code == 0
    assert "Could not retrieve deck" in result.output


# --- happy path: all cards available ---

def test_check_missing_all_available(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("2 Island\n1 Forest\n")
    _setup(tmp_path, available_cards=["4 Island", "3 Forest"])

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Total cards in deck: 3" in result.output
    assert "All cards can be found" in result.output


# --- some cards completely missing ---

def test_check_missing_some_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("2 Island\n1 Lightning Bolt\n")
    _setup(tmp_path, available_cards=["1 Island"])

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Missing cards:" in result.output
    assert "Lightning Bolt" in result.output
    # "All cards can be found" must NOT appear
    assert "All cards can be found" not in result.output


# --- cards available in other configured decks ---

def test_check_missing_cards_in_other_decks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("1 Lightning Bolt\n")
    _setup(
        tmp_path,
        available_cards=[],
        deck_cards_by_name={"other_deck": ["1 Lightning Bolt"]},
    )

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Cards available in other decks" in result.output
    assert "Lightning Bolt" in result.output
    assert "other_deck" in result.output
    # Completely missing section must not appear (card is sourced from other deck)
    assert "All cards can be found" in result.output


# --- partially sourced from other decks, remainder still missing ---

def test_check_missing_partial_from_other_deck(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    deck_file = tmp_path / "target.txt"
    deck_file.write_text("3 Lightning Bolt\n")  # need 3, other deck only has 1
    _setup(
        tmp_path,
        available_cards=[],
        deck_cards_by_name={"other_deck": ["1 Lightning Bolt"]},
    )

    result = CliRunner().invoke(cli, ["check-missing-cards", "--deck-file", str(deck_file)])

    assert result.exit_code == 0
    assert "Missing cards:" in result.output
    assert "Cards available in other decks" in result.output


# --- via --moxfield-id (mocked) ---

def test_check_missing_via_moxfield_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path, available_cards=["2 Island"])

    with patch("mtg_utils.commands.check_missing_cards.get_deck_list", return_value=["1 Island"]):
        result = CliRunner().invoke(cli, ["check-missing-cards", "--moxfield-id", "deck-id"])

    assert result.exit_code == 0
    assert "Total cards in deck: 1" in result.output
    assert "All cards can be found" in result.output
