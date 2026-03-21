import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mtg_utils.main import cli


def _make_config(tmp_path, decks=None):
    config = {
        "binder_id": "test-binder",
        "decks": decks or {},
        "purchased_file": "card_library/purchased.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    return config


def _run(tmp_path, library, deck_lists=None, extra_args=None):
    deck_lists = deck_lists or []
    runner = CliRunner()
    with patch("mtg_utils.commands.update_card_library.get_library", return_value=library):
        with patch(
            "mtg_utils.commands.update_card_library.get_deck_list",
            side_effect=deck_lists if deck_lists else [[]],
        ):
            return runner.invoke(cli, ["update-card-library"] + (extra_args or []))


# --- owned cards written ---


@pytest.mark.integration
def test_update_library_writes_owned_cards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)

    result = _run(tmp_path, library=["3 Island", "2 Forest"])

    assert result.exit_code == 0
    owned = (tmp_path / "card_library" / "owned_cards.txt").read_text()
    assert "3 Island" in owned
    assert "2 Forest" in owned


# --- available = owned minus deck ---


@pytest.mark.integration
def test_update_library_available_subtracts_deck(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"my_deck": {"file": "card_library/decks/my_deck.txt", "id": "d1"}})

    result = _run(tmp_path, library=["3 Island", "2 Forest"], deck_lists=[["1 Island"]])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # 3 owned - 1 in deck = 2
    assert "2 Forest" in available  # untouched


# --- purchased file created when absent ---


@pytest.mark.integration
def test_update_library_creates_purchased_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)

    result = _run(tmp_path, library=["1 Island"])

    assert result.exit_code == 0
    assert (tmp_path / "card_library" / "purchased.txt").exists()


# --- purchased cards increase available count ---


@pytest.mark.integration
def test_update_library_purchased_cards_added(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)
    (tmp_path / "card_library").mkdir()
    (tmp_path / "card_library" / "purchased.txt").write_text("Island\nIsland\n")

    result = _run(tmp_path, library=["2 Island"])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # only owned; purchased no longer merged into available_cards.txt
    purchased_formatted = (tmp_path / "card_library" / "purchased_formatted.txt").read_text()
    assert "2 Island" in purchased_formatted


# --- warning when deck needs more than owned ---


@pytest.mark.integration
def test_update_library_warns_on_unavailable_cards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output


# --- deck file written from Moxfield response ---


@pytest.mark.integration
def test_update_library_deck_file_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"alpha": {"file": "card_library/decks/alpha.txt", "id": "d1"}})

    result = _run(tmp_path, library=["2 Lightning Bolt"], deck_lists=[["1 Lightning Bolt"]])

    assert result.exit_code == 0
    deck_content = (tmp_path / "card_library" / "decks" / "alpha.txt").read_text()
    assert "1 Lightning Bolt" in deck_content


# --- shared_decks: child deck does not consume from pool ---


@pytest.mark.integration
def test_update_library_shared_decks_no_extra_consumption(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "base": {"file": "card_library/decks/base.txt", "id": "base-id"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["base"],
            },
        },
    )

    # Both decks need 1 Lightning Bolt; owned = 2.
    # Without sharing: 2 - 1 - 1 = 0 available.
    # With sharing:    base uses 1, child reuses base's copy → 2 - 1 = 1 available.
    result = _run(
        tmp_path,
        library=["2 Lightning Bolt"],
        deck_lists=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "1 Lightning Bolt" in available


# --- shared_decks: warns when referenced deck does not exist ---


@pytest.mark.integration
def test_update_library_shared_deck_missing_reference_warns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["nonexistent"],
            },
        },
    )

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["1 Island"]])

    assert result.exit_code == 0
    assert "nonexistent" in result.output


# --- deck retrieval fails ---


@pytest.mark.integration
def test_update_library_deck_retrieval_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"broken": {"file": "card_library/decks/broken.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[[]])

    assert result.exit_code == 0
    assert "Failed to retrieve broken deck" in result.output


# --- purchased card not previously in library ---


@pytest.mark.integration
def test_update_library_purchased_card_not_in_library(tmp_path, monkeypatch):
    """Purchased card not in owned library is written to purchased_formatted.txt but not available_cards.txt."""
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)
    (tmp_path / "card_library").mkdir()
    (tmp_path / "card_library" / "purchased.txt").write_text("Forest\n")

    result = _run(tmp_path, library=["2 Island"])  # Island owned, Forest only purchased

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "Forest" not in available
    assert "2 Island" in available
    purchased_formatted = (tmp_path / "card_library" / "purchased_formatted.txt").read_text()
    assert "1 Forest" in purchased_formatted


# --- warning includes sharing details and already-used info ---


@pytest.mark.integration
def test_update_library_unavailable_with_sharing_and_already_used(tmp_path, monkeypatch):
    """
    When a card is unavailable and the deck has shared_decks:
      - shared_details is non-empty  → covers 'sharing:' in warning message
      - already_used > 0             → covers 'already used:' in warning message
    Setup: library has 0 Lightning Bolt; 'base' consumes 1 (but fails), then
    'child' needs 3 sharing from 'base' (shared=1, consume=2, available=-1 < 2).
    """
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
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
        tmp_path,
        library=[],  # no owned cards
        deck_lists=[["1 Lightning Bolt"], ["3 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "sharing" in result.output
    assert "already used" in result.output


# --- same card consumed by two independent decks (used_cards +=) ---


@pytest.mark.integration
def test_update_library_same_card_in_multiple_decks(tmp_path, monkeypatch):
    """Second deck using the same card increments used_cards (the += branch)."""
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"},
            "beta": {"file": "card_library/decks/beta.txt", "id": "b1"},
        },
    )

    result = _run(tmp_path, library=["4 Island"], deck_lists=[["1 Island"], ["1 Island"]])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # 4 owned - 1 alpha - 1 beta = 2


# --- multiple shared_decks: no common card across shared decks ---


@pytest.mark.integration
def test_update_library_multiple_shared_decks_no_common(tmp_path, monkeypatch):
    """
    Child shares from two decks; no card is common to both shared decks.
    Covers: multi-shared-deck header, '(no cards common)' message,
            exclusive-cards per shared deck, and '0 cards' for empty deck.
    """
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"},
            "gamma": {"file": "card_library/decks/gamma.txt", "id": "g1"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "c1",
                "shared_decks": ["alpha", "gamma"],
            },
        },
    )

    result = _run(
        tmp_path,
        library=["1 Lightning Bolt", "1 Forest"],
        deck_lists=[
            ["1 Lightning Bolt"],  # alpha — consumes the only library copy
            ["1 Forest"],  # gamma (Forest not in child)
            ["1 Lightning Bolt"],  # child — must share LB from alpha
        ],
    )

    assert result.exit_code == 0
    assert "child" in result.output
    assert "alpha" in result.output
    assert "gamma" in result.output
    assert "cards" in result.output  # alpha has 1 exclusive card (Lightning Bolt)
    assert "0 cards" in result.output  # gamma has no cards matching child


# --- multiple shared_decks: common card in both shared decks ---


@pytest.mark.integration
def test_update_library_multiple_shared_decks_with_common(tmp_path, monkeypatch):
    """
    Child shares from two decks; Lightning Bolt is in BOTH shared decks.
    Covers the 'Common across shared decks' display branch.
    """
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"},
            "beta": {"file": "card_library/decks/beta.txt", "id": "b1"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "c1",
                "shared_decks": ["alpha", "beta"],
            },
        },
    )

    result = _run(
        tmp_path,
        library=["3 Lightning Bolt"],
        deck_lists=[
            ["1 Lightning Bolt"],  # alpha
            ["1 Lightning Bolt"],  # beta
            ["1 Lightning Bolt"],  # child — library has enough, sharing not needed
        ],
    )

    assert result.exit_code == 0
    # Rich truncates sub-panel titles at 80-column CliRunner width; match the visible prefix
    assert "Common across" in result.output
    assert "Lightning Bolt" in result.output


# --- custom config file path ---


@pytest.mark.integration
def test_update_library_custom_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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

    result = _run(tmp_path, library=["1 Forest"], extra_args=["--config-file", str(cfg_path)])

    assert result.exit_code == 0
    assert (tmp_path / "card_library" / "owned_cards.txt").exists()


# --- purchased * marker in missing-cards warning ---


@pytest.mark.integration
def test_update_library_purchased_marker_in_unavailable_warning(tmp_path, monkeypatch):
    """Unavailable card that is in purchased_formatted.txt shows * in the warning."""
    monkeypatch.chdir(tmp_path)
    config = {
        "binder_id": "test-binder",
        "decks": {"big": {"file": "card_library/decks/big.txt", "id": "d1"}},
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "card_library").mkdir()
    (tmp_path / "card_library" / "purchased_formatted.txt").write_text("4 Island\n")

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "*" in result.output


@pytest.mark.integration
def test_update_library_no_purchased_marker_when_not_purchased(tmp_path, monkeypatch):
    """Unavailable card NOT in purchased_formatted.txt shows no * in the warning."""
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "*" not in result.output


@pytest.mark.integration
def test_update_library_purchased_formatted_file_missing_is_handled(tmp_path, monkeypatch):
    """purchased_formatted_file key set but file absent → FileNotFoundError silently ignored."""
    monkeypatch.chdir(tmp_path)
    config = {
        "binder_id": "test-binder",
        "decks": {"big": {"file": "card_library/decks/big.txt", "id": "d1"}},
        "purchased_file": "card_library/purchased.txt",
        "purchased_formatted_file": "card_library/purchased_formatted.txt",
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    # purchased_formatted.txt intentionally NOT created

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output


# --- Rich panel titles ---


@pytest.mark.integration
def test_update_library_deck_sync_panel(repo):
    """'Deck sync' Panel title appears in output after a successful run."""
    repo(decks={"alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"}})
    with patch("mtg_utils.commands.update_card_library.get_library", return_value=["2 Island"]):
        with patch("mtg_utils.commands.update_card_library.get_deck_list", return_value=["1 Island"]):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "Deck sync" in result.output


@pytest.mark.integration
def test_update_library_unavailable_panel(repo):
    """'WARNING: Unavailable cards' Panel title appears when a deck needs more cards than owned."""
    repo(decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})
    with patch("mtg_utils.commands.update_card_library.get_library", return_value=["1 Island"]):
        with patch("mtg_utils.commands.update_card_library.get_deck_list", return_value=["4 Island"]):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "WARNING: Unavailable cards" in result.output


@pytest.mark.integration
def test_update_library_shared_decks_panel(repo):
    """'Shared decks' Panel title appears when a deck has shared_decks configured."""
    repo(
        decks={
            "base": {"file": "card_library/decks/base.txt", "id": "base-id"},
            "child": {
                "file": "card_library/decks/child.txt",
                "id": "child-id",
                "shared_decks": ["base"],
            },
        }
    )
    with patch("mtg_utils.commands.update_card_library.get_library", return_value=["2 Lightning Bolt"]):
        with patch(
            "mtg_utils.commands.update_card_library.get_deck_list",
            side_effect=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
        ):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "base" in result.output
    assert "*" not in result.output


# --- multi-shared-deck with one missing shared deck (covers `continue` branch) ---


@pytest.mark.integration
def test_update_library_multiple_shared_decks_one_missing(tmp_path, monkeypatch):
    """
    Child has shared_decks: [alpha, nonexistent]; 'nonexistent' is not a configured deck.
    The inner loop should hit the `continue` branch for the missing deck name.
    """
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
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
        tmp_path,
        library=["2 Lightning Bolt"],
        deck_lists=[
            ["1 Lightning Bolt"],  # alpha
            ["1 Lightning Bolt"],  # child — shares from alpha; nonexistent is skipped
        ],
    )

    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "child" in result.output


# --- two decks both with shared_decks → side-by-side panel grid (lines 281-288) ---


@pytest.mark.integration
def test_update_library_two_sharing_decks_side_by_side(tmp_path, monkeypatch):
    """
    Two decks each with shared_decks results in two entries in deck_panel_specs.
    The loop chunking logic prints them side-by-side via the `if len(chunk) == 2` branch.
    """
    monkeypatch.chdir(tmp_path)
    _make_config(
        tmp_path,
        decks={
            "base": {"file": "card_library/decks/base.txt", "id": "b1"},
            "child1": {
                "file": "card_library/decks/child1.txt",
                "id": "c1",
                "shared_decks": ["base"],
            },
            "child2": {
                "file": "card_library/decks/child2.txt",
                "id": "c2",
                "shared_decks": ["base"],
            },
        },
    )

    result = _run(
        tmp_path,
        library=["3 Lightning Bolt"],
        deck_lists=[
            ["1 Lightning Bolt"],  # base
            ["1 Lightning Bolt"],  # child1
            ["1 Lightning Bolt"],  # child2
        ],
    )

    assert result.exit_code == 0
    assert "child1" in result.output
    assert "child2" in result.output
