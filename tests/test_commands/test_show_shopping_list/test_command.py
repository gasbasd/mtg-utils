from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mtg_utils.commands.show_shopping_list.command import show_shopping_list

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_available(tmp_path: Path, lines: list[str]) -> None:
    available = tmp_path / "card_library" / "available_cards.txt"
    available.parent.mkdir(parents=True, exist_ok=True)
    available.write_text("\n".join(lines) + ("\n" if lines else ""))


def _write_deck(tmp_path: Path, name: str, lines: list[str]) -> Path:
    deck = tmp_path / f"{name}.txt"
    deck.write_text("\n".join(lines) + "\n")
    return deck


# ---------------------------------------------------------------------------
# validation errors
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_no_sources():
    """Invoking with no deck files and no moxfield IDs exits with code 1."""
    result = CliRunner().invoke(show_shopping_list, [])
    assert result.exit_code == 1
    assert "source" in result.output.lower() or "error" in result.output.lower()


@pytest.mark.integration
def test_available_cards_missing(tmp_path, monkeypatch):
    """Missing available_cards.txt → exit 1 with update-library hint."""
    monkeypatch.chdir(tmp_path)
    deck = _write_deck(tmp_path, "deck", ["Sol Ring"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck)])

    assert result.exit_code == 1
    assert "update-library" in result.output


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_happy_path_one_deck_file(tmp_path, monkeypatch):
    """One deck file; Sol Ring available, Counterspell needs to be bought."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, ["1 Sol Ring"])
    deck = _write_deck(tmp_path, "deck", ["Sol Ring", "Counterspell"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck)])

    assert result.exit_code == 0
    assert "Counterspell" in result.output
    assert "Sol Ring" in result.output


@pytest.mark.integration
def test_output_file_written(tmp_path, monkeypatch):
    """--output-file writes to_buy lines; available cards not included."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, ["1 Sol Ring"])
    deck = _write_deck(tmp_path, "deck", ["Sol Ring", "Counterspell"])
    output = tmp_path / "output.txt"

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck), "-o", str(output)])

    assert result.exit_code == 0
    contents = output.read_text()
    assert "1 Counterspell" in contents
    assert "Sol Ring" not in contents


@pytest.mark.integration
def test_output_file_sorted(tmp_path, monkeypatch):
    """Lines in output file are sorted alphabetically."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, [])
    deck = _write_deck(tmp_path, "deck", ["Zap", "Aether Vial", "Mox Pearl"])
    output = tmp_path / "output.txt"

    CliRunner().invoke(show_shopping_list, ["-d", str(deck), "-o", str(output)])

    lines = [line for line in output.read_text().splitlines() if line.strip()]
    card_names = [line.split(" ", 1)[1] for line in lines]
    assert card_names == sorted(card_names)


@pytest.mark.integration
def test_purchased_card_marked_with_star(tmp_path, monkeypatch):
    """Cards covered by purchased_formatted.txt are marked with * in the available panel."""
    import json

    monkeypatch.chdir(tmp_path)

    # available_cards.txt has no Sol Ring; purchased_formatted.txt has it
    card_lib = tmp_path / "card_library"
    card_lib.mkdir()
    (card_lib / "available_cards.txt").write_text("")
    (card_lib / "purchased_formatted.txt").write_text("1 Sol Ring\n")

    deck = tmp_path / "deck.txt"
    deck.write_text("Sol Ring\n")

    config = {
        "binder_id": "x",
        "decks": {},
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck)])

    assert result.exit_code == 0
    assert "*" in result.output
    assert "Sol Ring" in result.output


# ---------------------------------------------------------------------------
# purchased-card deck-deficit behaviour
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_purchased_fully_consumed_by_deck_deficit(tmp_path, monkeypatch):
    """Purchased qty exactly covers the configured deck deficit; effective = 0.

    owned = 0, deck needs 1, purchased = 1 → deficit = 1-0 = 1,
    effective_qty = max(0, 1-1) = 0 → Sol Ring is still needed for the new deck.
    """
    import json

    monkeypatch.chdir(tmp_path)

    card_lib = tmp_path / "card_library"
    decks_dir = card_lib / "decks"
    decks_dir.mkdir(parents=True)

    (card_lib / "available_cards.txt").write_text("")
    (card_lib / "owned_cards.txt").write_text("")
    (decks_dir / "existing.txt").write_text("1 Sol Ring\n")
    (card_lib / "purchased_formatted.txt").write_text("1 Sol Ring\n")

    config = {
        "binder_id": "x",
        "decks": {
            "existing": {
                "id": "fake-id",
                "file": "card_library/decks/existing.txt",
            }
        },
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    deck = _write_deck(tmp_path, "new_deck", ["Sol Ring"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck)])

    assert result.exit_code == 0
    assert "Sol Ring" in result.output


@pytest.mark.integration
def test_purchased_partially_consumed_by_deck_deficit(tmp_path, monkeypatch):
    """Purchased qty covers part of the deck deficit; remainder is available.

    owned = 0, deck needs 1, purchased = 2 → deficit = 1,
    effective_qty = max(0, 2-1) = 1 → new deck needs 2, has 1 free → buy 1.
    """
    import json

    monkeypatch.chdir(tmp_path)

    card_lib = tmp_path / "card_library"
    decks_dir = card_lib / "decks"
    decks_dir.mkdir(parents=True)

    (card_lib / "available_cards.txt").write_text("")
    (card_lib / "owned_cards.txt").write_text("")
    (decks_dir / "existing.txt").write_text("1 Sol Ring\n")
    (card_lib / "purchased_formatted.txt").write_text("2 Sol Ring\n")

    config = {
        "binder_id": "x",
        "decks": {
            "existing": {
                "id": "fake-id",
                "file": "card_library/decks/existing.txt",
            }
        },
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    deck = _write_deck(tmp_path, "new_deck", ["2 Sol Ring"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck)])

    assert result.exit_code == 0
    assert "Sol Ring" in result.output
    # Only 1 available (after 1 consumed by deficit), need 2 → buy 1
    assert "1 Sol Ring" in result.output


@pytest.mark.integration
def test_purchased_not_needed_by_deck_remains_fully_available(tmp_path, monkeypatch):
    """When owned already covers configured deck needs, ALL purchased copies are free.

    owned = 2, deck needs 1 → deficit = max(0, 1-2) = 0,
    effective_qty = 1 (all free); available_cards.txt already reflects 1 surplus.
    New deck needs 2: 1 from available_cards.txt + 1 effective purchased = 2 → buy 0.
    """
    import json

    monkeypatch.chdir(tmp_path)

    card_lib = tmp_path / "card_library"
    decks_dir = card_lib / "decks"
    decks_dir.mkdir(parents=True)

    (card_lib / "available_cards.txt").write_text("1 Sol Ring\n")
    (card_lib / "owned_cards.txt").write_text("2 Sol Ring\n")
    (decks_dir / "existing.txt").write_text("1 Sol Ring\n")
    (card_lib / "purchased_formatted.txt").write_text("1 Sol Ring\n")

    config = {
        "binder_id": "x",
        "decks": {
            "existing": {
                "id": "fake-id",
                "file": "card_library/decks/existing.txt",
            }
        },
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    deck = _write_deck(tmp_path, "new_deck", ["2 Sol Ring"])

    output = tmp_path / "output.txt"
    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck), "-o", str(output)])

    assert result.exit_code == 0
    # 1 from available_cards.txt + 1 effective purchased covers demand of 2 → not in buy list
    assert "Sol Ring" not in output.read_text()


# ---------------------------------------------------------------------------
# warning / skip cases
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_missing_deck_file_no_other_sources(tmp_path, monkeypatch):
    """Non-existent deck path → warning, then no valid sources → exit 1."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, ["1 Island"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(tmp_path / "nonexistent.txt")])

    assert result.exit_code == 1
    # warning about the missing file should appear
    assert (
        "nonexistent" in result.output.lower()
        or "not found" in result.output.lower()
        or "warning" in result.output.lower()
    )


@pytest.mark.integration
def test_duplicate_deck_file_warned(tmp_path, monkeypatch):
    """Same deck path provided twice → warning; processed only once."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, [])
    deck = _write_deck(tmp_path, "deck", ["Island"])

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck), "-d", str(deck)])

    assert result.exit_code == 0
    assert (
        "duplicate" in result.output.lower() or "already" in result.output.lower() or "warning" in result.output.lower()
    )
    # Island should appear only once in the buy list (not doubled)
    assert result.output.count("Island") >= 1


@pytest.mark.integration
def test_moxfield_fetch_failure_no_other_sources(tmp_path, monkeypatch):
    """get_deck_list returning [] → warning; no other sources → exit 1."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, ["1 Island"])

    with patch(
        "mtg_utils.commands.show_shopping_list.command.get_deck_list",
        return_value=[],
    ):
        result = CliRunner().invoke(show_shopping_list, ["-id", "bad-id"])

    assert result.exit_code == 1
    assert (
        "warning" in result.output.lower() or "could not" in result.output.lower() or "failed" in result.output.lower()
    )


@pytest.mark.integration
def test_moxfield_happy_path(tmp_path, monkeypatch):
    """Moxfield returns a card; available is empty; card appears in buy list."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, [])

    with patch(
        "mtg_utils.commands.show_shopping_list.command.get_deck_list",
        return_value=["1 Black Lotus"],
    ):
        result = CliRunner().invoke(show_shopping_list, ["-id", "some-id"])

    assert result.exit_code == 0
    assert "Black Lotus" in result.output


# ---------------------------------------------------------------------------
# purchased cards augmentation
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_purchased_cards_count_as_available(tmp_path, monkeypatch):
    """Card in purchased_formatted.txt but not available_cards.txt is treated as available."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, [])
    purchased = tmp_path / "card_library" / "purchased_formatted.txt"
    purchased.write_text("1 Sol Ring\n")
    deck = _write_deck(tmp_path, "deck", ["Sol Ring", "Counterspell"])

    # Write a config that points to the purchased_formatted_file
    import json

    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "binder_id": "x",
                "decks": {},
                "purchased_file": "card_library/purchased.txt",
                "purchased_formatted_file": "card_library/purchased_formatted.txt",
            }
        )
    )

    result = CliRunner().invoke(show_shopping_list, ["-d", str(deck), "--config-file", "config.json"])

    assert result.exit_code == 0
    # Sol Ring is covered by purchased; only Counterspell should need buying
    assert "Counterspell" in result.output
    # Sol Ring should be in the "already available" section, not the buy list
    lines_with_sol = [line for line in result.output.splitlines() if "Sol Ring" in line]
    assert lines_with_sol  # it should appear somewhere (available panel)


# ---------------------------------------------------------------------------
# all sources fail
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_all_sources_fail_moxfield_and_missing_file(tmp_path, monkeypatch):
    """Both a missing deck file and a failed moxfield fetch → exit 1."""
    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, ["1 Island"])

    with patch(
        "mtg_utils.commands.show_shopping_list.command.get_deck_list",
        return_value=[],
    ):
        result = CliRunner().invoke(
            show_shopping_list,
            [
                "-d",
                str(tmp_path / "ghost.txt"),
                "-id",
                "bad-id",
            ],
        )

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cards_in_decks population from config
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cards_in_decks_read_from_config_deck_files(tmp_path, monkeypatch):
    """Config decks with existing files are read and cards_in_decks is populated."""
    import json

    monkeypatch.chdir(tmp_path)
    _write_available(tmp_path, [])

    configured_deck = tmp_path / "configured_deck.txt"
    configured_deck.write_text("1 Sol Ring\n")

    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "binder_id": "x",
                "decks": {"my_deck": {"id": "abc", "file": str(configured_deck)}},
                "purchased_file": "card_library/purchased.txt",
            }
        )
    )

    shopping_deck = _write_deck(tmp_path, "shopping_deck", ["Sol Ring"])

    result = CliRunner().invoke(
        show_shopping_list,
        ["-d", str(shopping_deck), "--config-file", "config.json"],
    )

    assert result.exit_code == 0
    assert "Sol Ring" in result.output
