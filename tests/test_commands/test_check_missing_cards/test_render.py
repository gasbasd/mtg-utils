import pytest

from mtg_utils.commands.check_missing_cards import render as render_module
from mtg_utils.commands.check_missing_cards.render import render_results


@pytest.mark.unit
class TestRenderResults:
    def test_all_available_no_raise(self):
        """Renders without raising when all cards are available."""
        render_results(
            available_in_deck=["2 Island", "1 Forest"],
            completely_missing_cards=[],
            partially_missing_cards=[],
            cards_by_deck={},
            purchased_names=set(),
            owned_dict={"Island": 2, "Forest": 1},
            total=3,
        )

    def test_completely_missing_no_raise(self):
        render_results(
            available_in_deck=[],
            completely_missing_cards=[("Lightning Bolt", 4)],
            partially_missing_cards=[],
            cards_by_deck={},
            purchased_names=set(),
            owned_dict={},
            total=4,
        )

    def test_partially_missing_single_deck_no_raise(self):
        render_results(
            available_in_deck=[],
            completely_missing_cards=[],
            partially_missing_cards=[("Island", 1, "alpha (1)")],
            cards_by_deck={"alpha": [("Island", 1, 1)]},
            purchased_names=set(),
            owned_dict={},
            total=1,
        )

    def test_multiple_deck_rows_no_raise(self):
        """4 decks → exercises len(chunk) == 2 and single-panel remainder branches."""
        render_results(
            available_in_deck=[],
            completely_missing_cards=[],
            partially_missing_cards=[
                ("Island", 1, "deck_a (1)"),
                ("Forest", 1, "deck_b (1)"),
                ("Mountain", 1, "deck_c (1)"),
                ("Swamp", 1, "deck_d (1)"),
            ],
            cards_by_deck={
                "deck_a": [("Island", 1, 1)],
                "deck_b": [("Forest", 1, 1)],
                "deck_c": [("Mountain", 1, 1)],
                "deck_d": [("Swamp", 1, 1)],
            },
            purchased_names=set(),
            owned_dict={},
            total=4,
        )

    def test_purchased_marker_included_no_raise(self):
        """Cards in purchased_names show * marker — confirm no raise."""
        render_results(
            available_in_deck=["1 Island"],
            completely_missing_cards=[],
            partially_missing_cards=[],
            cards_by_deck={},
            purchased_names={"Island"},
            owned_dict={},
            total=1,
        )

    def test_available_and_missing_panels_do_not_force_height(self, monkeypatch):
        """Regression guard: adjacent availability panels should use natural height."""
        panel_kwargs: list[dict] = []

        class DummyPanel:
            def __init__(self, _renderable, **kwargs):
                panel_kwargs.append(kwargs)

        monkeypatch.setattr(render_module, "Panel", DummyPanel)
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(render_module, "side_by_side", lambda left, right: (left, right))
        monkeypatch.setattr(render_module, "panel_row", lambda panels: panels)

        render_results(
            available_in_deck=["2 Island"],
            completely_missing_cards=[("Forest", 1), ("Swamp", 1), ("Mountain", 1)],
            partially_missing_cards=[],
            cards_by_deck={},
            purchased_names=set(),
            owned_dict={"Island": 2},
            total=5,
        )

        titles = [kwargs.get("title", "") for kwargs in panel_kwargs]
        assert any(title.startswith("Available:") for title in titles)
        assert any(title.startswith("Missing:") for title in titles)
        assert all(
            "height" not in kwargs
            for kwargs in panel_kwargs
            if kwargs.get("title", "").startswith(("Available:", "Missing:"))
        )

    def test_deck_breakdown_panels_do_not_force_height(self, monkeypatch):
        """Regression guard: deck panels in rows should not force clipped heights."""
        panel_kwargs: list[dict] = []

        class DummyPanel:
            def __init__(self, _renderable, **kwargs):
                panel_kwargs.append(kwargs)

        monkeypatch.setattr(render_module, "Panel", DummyPanel)
        monkeypatch.setattr(render_module.console, "print", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(render_module, "side_by_side", lambda left, right: (left, right))
        monkeypatch.setattr(render_module, "panel_row", lambda panels: panels)

        render_results(
            available_in_deck=["1 Island"],
            completely_missing_cards=[],
            partially_missing_cards=[("Sol Ring", 1, "alpha (1)")],
            cards_by_deck={
                "alpha": [("Sol Ring", 1, 1)],
                "beta": [("Counterspell", 1, 1), ("Brainstorm", 1, 1), ("Ponder", 1, 1)],
            },
            purchased_names=set(),
            owned_dict={"Island": 1},
            total=2,
        )

        deck_titles = [kwargs.get("title", "") for kwargs in panel_kwargs if "cards needed" in kwargs.get("title", "")]
        assert len(deck_titles) == 2
        assert all("height" not in kwargs for kwargs in panel_kwargs if "cards needed" in kwargs.get("title", ""))
