import pytest

from mtg_utils.commands.check_missing_cards.logic import compute_missing_cards


@pytest.mark.unit
class TestComputeMissingCards:
    def test_all_available(self):
        deck = {"Island": 2, "Forest": 1}
        available = {"Island": 4, "Forest": 3}
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards(
            deck, available, available, {}
        )
        assert completely_missing == []
        assert partially_missing == []
        assert set(available_in_deck) == {"2 Island", "1 Forest"}
        assert cards_by_deck == {}

    def test_completely_missing_no_other_decks(self):
        deck = {"Lightning Bolt": 2}
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards(
            deck, {}, {}, {}
        )
        assert completely_missing == [("Lightning Bolt", 2)]
        assert partially_missing == []
        assert available_in_deck == []

    def test_partial_availability(self):
        """1 owned, 2 needed → 1 available_in_deck, 1 completely missing."""
        deck = {"Island": 2}
        available = {"Island": 1}
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards(
            deck, available, available, {}
        )
        assert completely_missing == [("Island", 1)]
        assert available_in_deck == ["1 Island"]

    def test_fully_covered_by_other_deck(self):
        """Other deck has enough copies: appears in partially_missing, not completely_missing."""
        deck = {"Island": 1}
        cards_in_decks = {"Island": [("sibling", 2)]}
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards(
            deck, {}, {}, cards_in_decks
        )
        assert completely_missing == []
        assert len(partially_missing) == 1
        card_name, qty, deck_info = partially_missing[0]
        assert card_name == "Island"
        assert "sibling" in deck_info

    def test_partially_covered_by_other_deck(self):
        """Other deck only has 1, but 3 needed → 2 still completely missing."""
        deck = {"Island": 3}
        cards_in_decks = {"Island": [("sibling", 1)]}
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards(
            deck, {}, {}, cards_in_decks
        )
        assert ("Island", 2) in completely_missing
        assert len(partially_missing) == 1

    def test_cards_by_deck_populated(self):
        """cards_by_deck tracks which deck contributes how many of each card."""
        deck = {"Island": 1}
        cards_in_decks = {"Island": [("alpha", 1)]}
        _, _, _, cards_by_deck = compute_missing_cards(deck, {}, {}, cards_in_decks)
        assert "alpha" in cards_by_deck
        entries = cards_by_deck["alpha"]
        assert any(card_name == "Island" for card_name, _, _ in entries)

    def test_empty_deck(self):
        completely_missing, partially_missing, available_in_deck, cards_by_deck = compute_missing_cards({}, {}, {}, {})
        assert completely_missing == []
        assert partially_missing == []
        assert available_in_deck == []
        assert cards_by_deck == {}
