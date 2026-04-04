import io
from unittest.mock import patch

import pytest
from rich.console import Console

from mtg_utils.commands.update_card_library import render as render_module
from mtg_utils.commands.update_card_library.logic import DeckFetchResult
from mtg_utils.commands.update_card_library.render import (
    render_deck_sync_panel,
    render_failed_deck_warning,
    render_shared_deck_panels,
    render_unavailable_warnings,
)
from mtg_utils.utils.config import DeckConfig


def _deck_cfg(
    id: str = "fake",
    file: str = "fake.txt",
    shared_decks: list[str] | None = None,
) -> DeckConfig:
    return DeckConfig(id=id, file=file, shared_decks=shared_decks or [])


def _capture_err(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    cap = Console(file=buf, highlight=False)
    with patch("mtg_utils.commands.update_card_library.render.err_console", cap):
        fn(*args, **kwargs)
    return buf.getvalue()


def _capture_out(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    # Use a wide console so card names in narrow side-by-side panels are not truncated.
    cap = Console(file=buf, highlight=False, width=400)
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
    def _captured_panel_titles(self, monkeypatch, deck_cards, deck_configs):
        titles = []

        class _FakePanel:
            def __init__(self, renderable, title=None, border_style=None):
                self.renderable = renderable
                self.title = title
                self.border_style = border_style
                if title is not None:
                    titles.append(title)

        monkeypatch.setattr(render_module, "Panel", _FakePanel)
        monkeypatch.setattr(render_module, "panel_row", lambda panels: panels)
        monkeypatch.setattr(render_module, "side_by_side", lambda left, right: (left, right))
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)

        render_shared_deck_panels(deck_cards, deck_configs)
        return titles

    def _captured_shared_subpanels(self, monkeypatch, deck_cards, deck_configs):
        captured = []

        class _FakePanel:
            def __init__(self, renderable, title=None, border_style=None):
                self.renderable = renderable
                self.title = title
                self.border_style = border_style
                if title is not None and "[bold yellow1]" in title:
                    captured.append((title, renderable))

        monkeypatch.setattr(render_module, "Panel", _FakePanel)
        monkeypatch.setattr(render_module, "panel_row", lambda panels: panels)
        monkeypatch.setattr(render_module, "side_by_side", lambda left, right: (left, right))
        monkeypatch.setattr(render_module, "card_table", lambda rows: rows)
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)

        render_shared_deck_panels(deck_cards, deck_configs)
        return captured

    def test_no_shared_decks_shows_output(self):
        # Decks without shared_decks now produce a panel showing all their cards.
        deck_cards = {"base": {"Forest": 1}}
        deck_configs = {"base": _deck_cfg(id="b1", file="base.txt")}
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "base" in out
        assert "Forest" in out

    def test_no_shared_decks_shows_all_cards_label(self):
        # The sub-panel for a deck without shared_decks is labelled "All cards (N cards)".
        deck_cards = {"base": {"Forest": 2, "Island": 1}}
        deck_configs = {"base": _deck_cfg(id="b1", file="base.txt")}
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "All cards" in out

    def test_single_shared_deck_renders(self):
        # Cards shared with the base deck AND cards unique to child both appear.
        deck_cards = {
            "base": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1, "Swords to Plowshares": 1},
        }
        deck_configs = {
            "base": _deck_cfg(id="b1", file="base.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["base"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "child" in out
        assert "base" in out
        assert "Swords to Plowshares" in out

    def test_single_shared_deck_shows_only_in_panel(self):
        # A new "Only in {deck_name}" sub-panel lists cards not present in any shared deck.
        deck_cards = {
            "base": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1, "Counterspell": 2},
        }
        deck_configs = {
            "base": _deck_cfg(id="b1", file="base.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["base"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "Only in child" in out
        assert "Counterspell" in out

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

    def test_common_and_shared_and_only_panels_split_overlap_quantity(self, monkeypatch):
        # current deck 16, shared decks gretchen 14 and weavers 12 -> split as 12/2/2
        deck_cards = {
            "gretchen": {"Snow-Covered Island": 14},
            "weavers": {"Snow-Covered Island": 12},
            "current": {"Snow-Covered Island": 16},
        }
        deck_configs = {
            "current": _deck_cfg(id="c1", file="current.txt", shared_decks=["gretchen", "weavers"]),
        }

        panels = self._captured_shared_subpanels(monkeypatch, deck_cards, deck_configs)

        assert (
            "[bold yellow1]Common across shared decks (12 cards)[/bold yellow1]",
            [("Snow-Covered Island", 12)],
        ) in panels
        assert ("[bold yellow1]gretchen (2 cards)[/bold yellow1]", [("Snow-Covered Island", 2)]) in panels
        assert (
            "[bold yellow1]Only in current (2 cards)[/bold yellow1]",
            [("Snow-Covered Island", 2)],
        ) in panels

    def test_single_shared_deck_panel_uses_min_overlap_with_current_deck(self, monkeypatch):
        deck_cards = {
            "tatyova": {"Snow-Covered Island": 14},
            "gretchen": {"Snow-Covered Island": 16},
        }
        deck_configs = {
            "gretchen": _deck_cfg(id="c1", file="child.txt", shared_decks=["tatyova"]),
        }

        panels = self._captured_shared_subpanels(monkeypatch, deck_cards, deck_configs)

        assert ("[bold yellow1]tatyova (14 cards)[/bold yellow1]", [("Snow-Covered Island", 14)]) in panels

    def test_per_shared_deck_exclusive_panel_uses_min_overlap(self, monkeypatch):
        deck_cards = {
            "tatyova": {"Snow-Covered Island": 14},
            "weavers": {"Forest": 2},
            "gretchen": {"Snow-Covered Island": 16, "Forest": 2},
        }
        deck_configs = {
            "gretchen": _deck_cfg(id="c1", file="child.txt", shared_decks=["tatyova", "weavers"]),
        }

        panels = self._captured_shared_subpanels(monkeypatch, deck_cards, deck_configs)

        assert ("[bold yellow1]tatyova (14 cards)[/bold yellow1]", [("Snow-Covered Island", 14)]) in panels

    def test_only_in_deck_panel_title_uses_total_quantity(self, monkeypatch):
        deck_cards = {
            "base": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1, "Counterspell": 4},
        }
        deck_configs = {
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["base"]),
        }

        titles = self._captured_panel_titles(monkeypatch, deck_cards, deck_configs)

        assert "[bold yellow1]Only in child (4 cards)[/bold yellow1]" in titles

    def test_multiple_shared_decks_shows_only_in_panel(self):
        # Cards in child not found in any shared deck appear in "Only in {deck_name}" sub-panel.
        deck_cards = {
            "alpha": {"Lightning Bolt": 1},
            "beta": {"Forest": 1},
            "child": {"Lightning Bolt": 1, "Forest": 1, "Brainstorm": 1},
        }
        deck_configs = {
            "alpha": _deck_cfg(id="a1", file="alpha.txt"),
            "beta": _deck_cfg(id="b1", file="beta.txt"),
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["alpha", "beta"]),
        }
        out = _capture_out(render_shared_deck_panels, deck_cards, deck_configs)
        assert "Only in child" in out
        assert "Brainstorm" in out

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

    def test_shared_subpanels_grouped_two_by_two_not_three(self, monkeypatch):
        # Regression guard: a 4-panel shared section must render as 2+2, never 3+1.
        row_sizes = []

        def fake_panel_row(panels):
            row_sizes.append(len(panels))
            return "row"

        monkeypatch.setattr(render_module, "panel_row", fake_panel_row)
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)

        deck_cards = {
            "alpha": {"Lightning Bolt": 1, "Forest": 1},
            "beta": {"Lightning Bolt": 1, "Island": 1},
            "child": {"Lightning Bolt": 1, "Forest": 1, "Island": 1, "Brainstorm": 1},
        }
        deck_configs = {
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["alpha", "beta"]),
        }

        render_shared_deck_panels(deck_cards, deck_configs)

        assert row_sizes == [2, 2]

    def test_shared_subpanels_with_odd_remainder_use_single_panel_row(self, monkeypatch):
        # Regression guard: a 3-panel shared section must render as 2+1, never a 3-column row.
        row_sizes = []

        def fake_panel_row(panels):
            row_sizes.append(len(panels))
            return "row"

        monkeypatch.setattr(render_module, "panel_row", fake_panel_row)
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)

        deck_cards = {
            "alpha": {"Forest": 1},
            "beta": {"Island": 1},
            "child": {"Forest": 1, "Island": 1, "Brainstorm": 1},
        }
        deck_configs = {
            "child": _deck_cfg(id="c1", file="child.txt", shared_decks=["alpha", "beta"]),
        }

        render_shared_deck_panels(deck_cards, deck_configs)

        assert row_sizes == [2, 1]


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
