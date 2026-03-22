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
def test_writes_owned_cards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)

    result = _run(tmp_path, library=["3 Island", "2 Forest"])

    assert result.exit_code == 0
    owned = (tmp_path / "card_library" / "owned_cards.txt").read_text()
    assert "3 Island" in owned
    assert "2 Forest" in owned


# ---------------------------------------------------------------------------
# Available cards
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_available_subtracts_deck(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"my_deck": {"file": "card_library/decks/my_deck.txt", "id": "d1"}})

    result = _run(tmp_path, library=["3 Island", "2 Forest"], deck_lists=[["1 Island"]])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available  # 3 owned - 1 in deck = 2
    assert "2 Forest" in available  # untouched


@pytest.mark.integration
def test_same_card_in_multiple_decks(tmp_path, monkeypatch):
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


# ---------------------------------------------------------------------------
# Purchased cards
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_creates_purchased_file_when_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)

    result = _run(tmp_path, library=["1 Island"])

    assert result.exit_code == 0
    assert (tmp_path / "card_library" / "purchased.txt").exists()


@pytest.mark.integration
def test_purchased_cards_written_to_formatted_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)
    (tmp_path / "card_library").mkdir()
    (tmp_path / "card_library" / "purchased.txt").write_text("Island\nIsland\n")

    result = _run(tmp_path, library=["2 Island"])

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "2 Island" in available
    purchased_formatted = (tmp_path / "card_library" / "purchased_formatted.txt").read_text()
    assert "2 Island" in purchased_formatted


@pytest.mark.integration
def test_purchased_card_not_in_library(tmp_path, monkeypatch):
    """Purchased card not in owned library is written to purchased_formatted.txt but not available_cards.txt."""
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path)
    (tmp_path / "card_library").mkdir()
    (tmp_path / "card_library" / "purchased.txt").write_text("Forest\n")

    result = _run(tmp_path, library=["2 Island"])

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
def test_deck_file_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"alpha": {"file": "card_library/decks/alpha.txt", "id": "d1"}})

    result = _run(tmp_path, library=["2 Lightning Bolt"], deck_lists=[["1 Lightning Bolt"]])

    assert result.exit_code == 0
    deck_content = (tmp_path / "card_library" / "decks" / "alpha.txt").read_text()
    assert "1 Lightning Bolt" in deck_content


@pytest.mark.integration
def test_deck_retrieval_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"broken": {"file": "card_library/decks/broken.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[[]])

    assert result.exit_code == 0
    assert "Failed to retrieve broken deck" in result.output


@pytest.mark.integration
def test_deck_sync_panel(repo):
    """'Deck sync' Panel title appears in output after a successful run."""
    repo(decks={"alpha": {"file": "card_library/decks/alpha.txt", "id": "a1"}})
    with patch("mtg_utils.commands.update_card_library.command.get_library", return_value=["2 Island"]):
        with patch("mtg_utils.commands.update_card_library.command.get_deck_list", return_value=["1 Island"]):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "Deck sync" in result.output


# ---------------------------------------------------------------------------
# Unavailable cards warnings
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_warns_on_unavailable_cards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output


@pytest.mark.integration
def test_unavailable_panel_title(repo):
    """'WARNING: Unavailable cards' Panel title appears when a deck needs more cards than owned."""
    repo(decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})
    with patch("mtg_utils.commands.update_card_library.command.get_library", return_value=["1 Island"]):
        with patch("mtg_utils.commands.update_card_library.command.get_deck_list", return_value=["4 Island"]):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "WARNING: Unavailable cards" in result.output


@pytest.mark.integration
def test_unavailable_with_sharing_and_already_used(tmp_path, monkeypatch):
    """'sharing:' and 'already used:' both appear in the warning message."""
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


@pytest.mark.integration
def test_purchased_marker_in_unavailable_warning(tmp_path, monkeypatch):
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
def test_no_purchased_marker_when_not_purchased(tmp_path, monkeypatch):
    """Unavailable card NOT in purchased_formatted.txt shows no * in the warning."""
    monkeypatch.chdir(tmp_path)
    _make_config(tmp_path, decks={"big": {"file": "card_library/decks/big.txt", "id": "d1"}})

    result = _run(tmp_path, library=["1 Island"], deck_lists=[["4 Island"]])

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "*" not in result.output


@pytest.mark.integration
def test_purchased_formatted_file_missing_is_handled(tmp_path, monkeypatch):
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


# ---------------------------------------------------------------------------
# shared_decks
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_shared_decks_no_extra_consumption(tmp_path, monkeypatch):
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
        library=["2 Lightning Bolt"],
        deck_lists=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    available = (tmp_path / "card_library" / "available_cards.txt").read_text()
    assert "1 Lightning Bolt" in available


@pytest.mark.integration
def test_shared_deck_missing_reference_warns(tmp_path, monkeypatch):
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


@pytest.mark.integration
def test_shared_decks_panel(repo):
    """Shared decks panel appears when a deck has shared_decks configured."""
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
    with patch("mtg_utils.commands.update_card_library.command.get_library", return_value=["2 Lightning Bolt"]):
        with patch(
            "mtg_utils.commands.update_card_library.command.get_deck_list",
            side_effect=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
        ):
            result = CliRunner().invoke(cli, ["update-card-library"])
    assert result.exit_code == 0
    assert "base" in result.output
    assert "*" not in result.output


@pytest.mark.integration
def test_multiple_shared_decks_one_missing(tmp_path, monkeypatch):
    """'nonexistent' shared deck hits the `continue` branch in the render loop."""
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
        deck_lists=[["1 Lightning Bolt"], ["1 Lightning Bolt"]],
    )

    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "child" in result.output


@pytest.mark.integration
def test_multiple_shared_decks_no_common(tmp_path, monkeypatch):
    """No card common across both shared decks → '0 cards' sub-panel."""
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
            ["1 Lightning Bolt"],  # alpha
            ["1 Forest"],  # gamma (Forest not in child)
            ["1 Lightning Bolt"],  # child — shares LB from alpha
        ],
    )

    assert result.exit_code == 0
    assert "child" in result.output
    assert "alpha" in result.output
    assert "gamma" in result.output
    assert "0 cards" in result.output


@pytest.mark.integration
def test_multiple_shared_decks_with_common(tmp_path, monkeypatch):
    """Lightning Bolt in BOTH shared decks → 'Common across shared decks' sub-panel."""
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
            ["1 Lightning Bolt"],  # child
        ],
    )

    assert result.exit_code == 0
    assert "Common across" in result.output
    assert "Lightning Bolt" in result.output


@pytest.mark.integration
def test_two_sharing_decks_side_by_side(tmp_path, monkeypatch):
    """Two decks with shared_decks → side-by-side panel grid (len(chunk)==2 branch)."""
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


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_custom_config_file(tmp_path, monkeypatch):
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
