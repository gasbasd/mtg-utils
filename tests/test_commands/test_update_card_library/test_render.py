import io
from unittest.mock import patch

import pytest
from rich.console import Console

from mtg_utils.commands.update_card_library.logic import DeckFetchResult
from mtg_utils.commands.update_card_library.render import (
    render_deck_sync_panel,
    render_failed_deck_warning,
    render_shared_deck_panels,
    render_unavailable_warnings,
)
from mtg_utils.utils.config import DeckConfig


def _deck_cfg(**kwargs) -> DeckConfig:
    return DeckConfig(**({"id": "fake", "file": "fake.txt"} | kwargs))


def _capture_err(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    cap = Console(file=buf, highlight=False)
    with patch("mtg_utils.commands.update_card_library.render.err_console", cap):
        fn(*args, **kwargs)
    return buf.getvalue()


def _capture_out(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    cap = Console(file=buf, highlight=False)
    with patch("mtg_utils.commands.update_card_library.render.console", cap):
        fn(*args, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# render_unavailable_warnings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderUnavailableWarnings:
    def test_empty_dict_no_output(self):
        out = _capture_err(render_unavailable_warnings, {}, set())
        assert "WARNING" not in out

    def test_warning_panel_title(self):
        unavailable = {"big": [("Island", "4 Island (have 1)")]}
        out = _capture_err(render_unavailable_warnings, unavailable, set())
        assert "WARNING" in out
        assert "Unavailable cards" in out

    def test_purchased_marker_shown(self):
        unavailable = {"big": [("Island", "4 Island (have 1)")]}
        out = _capture_err(render_unavailable_warnings, unavailable, {"Island"})
        assert "*" in out

    def test_no_marker_when_not_purchased(self):
        unavailable = {"big": [("Island", "4 Island (have 1)")]}
        out = _capture_err(render_unavailable_warnings, unavailable, set())
        assert "*" not in out

    def test_detail_extracted_from_message(self):
        unavailable = {"big": [("Island", "4 Island (have 1, already used: 1 in alpha)")]}
        out = _capture_err(render_unavailable_warnings, unavailable, set())
        assert "Island" in out

    def test_multiple_decks_all_rendered(self):
        unavailable = {
            "alpha": [("Forest", "2 Forest (have 0)")],
            "beta": [("Mountain", "1 Mountain (have 0)")],
        }
        out = _capture_err(render_unavailable_warnings, unavailable, set())
        assert "alpha" in out
        assert "beta" in out


# ---------------------------------------------------------------------------
# render_shared_deck_panels
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderSharedDeckPanels:
    def test_no_shared_decks_no_output(self):
        deck_cards = {"base": {"Forest": 1}}
        deck_configs = {"base": _deck_cfg(id="b1", file="base.txt")}
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert out.strip() == ""

    def test_single_shared_deck_renders(self):
        deck_cards = {
            "base": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1},
        }
        deck_configs = {
            "base": _deck_cfg(id="b1", file="base.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["base"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "child" in out
        assert "base" in out

    def test_multiple_shared_decks_no_common(self):
        # alpha has Lightning Bolt, gamma has Forest — child only has Lightning Bolt
        # gamma sub-panel gets 0 exclusive cards
        deck_cards = {
            "alpha": {"Lightning Bolt": 1},
            "gamma": {"Forest": 1},
            "child": {"Lightning Bolt": 1},
        }
        deck_configs = {
            "alpha": _deck_cfg(id="a1", file="alpha.txt"),
            "gamma": _deck_cfg(id="g1", file="gamma.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["alpha", "gamma"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "0 cards" in out

    def test_multiple_shared_decks_with_common(self):
        # Lightning Bolt in BOTH alpha and beta → "Common across" sub-panel
        deck_cards = {
            "alpha": {"Lightning Bolt": 1},
            "beta": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1},
        }
        deck_configs = {
            "alpha": _deck_cfg(id="a1", file="alpha.txt"),
            "beta": _deck_cfg(id="b1", file="beta.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["alpha", "beta"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "Common across" in out

    def test_missing_shared_deck_skipped(self):
        # child references "nonexistent" which is not in deck_cards → no exception
        deck_cards = {"child": {"Lightning Bolt": 1}}
        deck_configs = {
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["nonexistent"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "child" in out

    def test_two_sharing_decks_side_by_side(self):
        # Two decks each with shared_decks → chunk size 2 → side_by_side branch
        deck_cards = {
            "base": {"Forest": 1},
            "child1": {"Forest": 1},
            "child2": {"Forest": 1},
        }
        deck_configs = {
            "base": _deck_cfg(id="b1", file="base.txt"),
            "child1": _deck_cfg(id="c1", file="child1.txt", shared_decks=["base"]),
            "child2": _deck_cfg(id="c2", file="child2.txt", shared_decks=["base"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "child1" in out
        assert "child2" in out

    def test_single_sharing_deck_odd_panel(self):
        # Three decks with shared_decks → first two side-by-side, third alone (len(chunk)==1)
        deck_cards = {
            "base": {"Forest": 1},
            "child1": {"Forest": 1},
            "child2": {"Forest": 1},
            "child3": {"Forest": 1},
        }
        deck_configs = {
            "base": _deck_cfg(id="b1", file="base.txt"),
            "child1": _deck_cfg(id="c1", file="child1.txt", shared_decks=["base"]),
            "child2": _deck_cfg(id="c2", file="child2.txt", shared_decks=["base"]),
            "child3": _deck_cfg(id="c3", file="child3.txt", shared_decks=["base"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "child3" in out


# ---------------------------------------------------------------------------
# render_failed_deck_warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderFailedDeckWarning:
    def test_deck_name_in_output(self):
        out = _capture_err(render_failed_deck_warning, "broken")
        assert "broken" in out
        assert "Failed to retrieve" in out


# ---------------------------------------------------------------------------
# render_deck_sync_panel
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderDeckSyncPanel:
    def test_deck_sync_title(self):
        results = [DeckFetchResult("alpha", True, "card_library/decks/alpha.txt", [], _deck_cfg())]
        out = _capture_out(render_deck_sync_panel, results)
        assert "Deck sync" in out

    def test_ok_result_shows_check(self):
        results = [DeckFetchResult("alpha", True, "card_library/decks/alpha.txt", [], _deck_cfg())]
        out = _capture_out(render_deck_sync_panel, results)
        assert "\u2713" in out

    def test_failed_result_shows_cross(self):
        results = [DeckFetchResult("broken", False, "\u2014", [], _deck_cfg())]
        out = _capture_out(render_deck_sync_panel, results)
        assert "failed" in out

    def test_multiple_results(self):
        results = [
            DeckFetchResult("alpha", True, "card_library/decks/alpha.txt", [], _deck_cfg()),
            DeckFetchResult("beta", False, "\u2014", [], _deck_cfg()),
        ]
        out = _capture_out(render_deck_sync_panel, results)
        assert "alpha" in out
        assert "beta" in out
