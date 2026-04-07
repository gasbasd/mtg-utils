import pytest

from mtg_utils.commands.show_shopping_list.logic import compute_shopping_list
from mtg_utils.utils.cards import parse_card_list_or_names

# ---------------------------------------------------------------------------
# compute_shopping_list
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeShoppingList:
    def test_two_decks_partial_overlap(self):
        """Two decks with overlapping cards; available covers one."""
        sources = [
            ("A", {"Sol Ring": 1, "Counterspell": 1}),
            ("B", {"Counterspell": 1, "Path to Exile": 1}),
        ]
        available = {"Sol Ring": 1}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == [
            ("Counterspell", 2, ["A", "B"], []),
            ("Path to Exile", 1, ["B"], []),
        ]
        assert already_available == [("Sol Ring", 1)]

    def test_all_cards_available(self):
        """Available pool covers all demand; nothing to buy."""
        sources = [
            ("deck", {"Island": 2, "Forest": 1}),
        ]
        available = {"Island": 10, "Forest": 5}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == []
        assert already_available == [("Forest", 1), ("Island", 2)]

    def test_no_available_pool(self):
        """Empty available dict; everything needs to be bought."""
        sources = [
            ("deck", {"Lightning Bolt": 4}),
        ]
        available = {}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == [("Lightning Bolt", 4, ["deck"], [])]
        assert already_available == []

    def test_multi_copy_demand(self):
        """Two decks each need 2 copies; available has 1 → buy 3."""
        sources = [
            ("A", {"Dark Ritual": 2}),
            ("B", {"Dark Ritual": 2}),
        ]
        available = {"Dark Ritual": 1}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == [("Dark Ritual", 3, ["A", "B"], [])]
        assert already_available == []

    def test_single_source_empty(self):
        """Source with empty card dict should produce no results."""
        sources = [("empty", {})]
        available = {"Island": 5}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == []
        assert already_available == []

    def test_to_buy_sorted_alphabetically(self):
        """to_buy entries are sorted by card name."""
        sources = [
            ("deck", {"Zap": 1, "Aether Vial": 1, "Mox Pearl": 1}),
        ]
        available = {}

        to_buy, _ = compute_shopping_list(sources, available, {})

        names = [name for name, _, _, __ in to_buy]
        assert names == sorted(names)

    def test_already_available_sorted_alphabetically(self):
        """already_available entries are sorted by card name."""
        sources = [
            ("deck", {"Zap": 1, "Aether Vial": 1, "Mox Pearl": 1}),
        ]
        available = {"Zap": 10, "Aether Vial": 10, "Mox Pearl": 10}

        _, already_available = compute_shopping_list(sources, available, {})

        assert already_available == sorted(already_available)

    def test_partial_availability_buys_difference(self):
        """Available covers some but not all; only the shortfall is in to_buy."""
        sources = [("deck", {"Counterspell": 4})]
        available = {"Counterspell": 3}

        to_buy, already_available = compute_shopping_list(sources, available, {})

        assert to_buy == [("Counterspell", 1, ["deck"], [])]
        assert already_available == []

    def test_no_sources(self):
        """Empty sources list produces empty results."""
        to_buy, already_available = compute_shopping_list([], {}, {})

        assert to_buy == []
        assert already_available == []

    def test_already_available_carries_demanded_qty(self):
        """already_available entries carry the total demanded quantity."""
        sources = [
            ("A", {"Counterspell": 2}),
            ("B", {"Counterspell": 1}),
        ]
        available = {"Counterspell": 10}

        _, already_available = compute_shopping_list(sources, available, {})

        assert already_available == [("Counterspell", 3)]

    def test_cards_in_decks_populated(self):
        """Cards in configured decks appear in config_deck_names."""
        sources = [("A", {"Sol Ring": 1})]
        available = {}
        cards_in_decks = {"Sol Ring": ["commander_deck", "other_deck"]}

        to_buy, _ = compute_shopping_list(sources, available, cards_in_decks)

        assert to_buy == [("Sol Ring", 1, ["A"], ["commander_deck", "other_deck"])]

    def test_cards_in_decks_not_in_to_buy_card(self):
        """cards_in_decks for a card not in to_buy doesn't affect results."""
        sources = [("A", {"Forest": 1})]
        available = {"Forest": 5}
        cards_in_decks = {"Sol Ring": ["some_deck"]}

        to_buy, already_available = compute_shopping_list(sources, available, cards_in_decks)

        assert to_buy == []
        assert already_available == [("Forest", 1)]


# ---------------------------------------------------------------------------
# parse_card_list_or_names
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseCardListOrNames:
    def test_with_quantity_prefix(self):
        result = parse_card_list_or_names(["2 Lightning Bolt"])
        assert result == {"Lightning Bolt": 2}

    def test_without_quantity_prefix(self):
        result = parse_card_list_or_names(["Lightning Bolt"])
        assert result == {"Lightning Bolt": 1}

    def test_mixed_format(self):
        result = parse_card_list_or_names(["2 Lightning Bolt", "Counterspell"])
        assert result == {"Lightning Bolt": 2, "Counterspell": 1}

    def test_empty_list(self):
        assert parse_card_list_or_names([]) == {}

    def test_qty_one_explicit(self):
        result = parse_card_list_or_names(["1 Sol Ring"])
        assert result == {"Sol Ring": 1}

    def test_multi_word_name_no_qty(self):
        result = parse_card_list_or_names(["Path to Exile"])
        assert result == {"Path to Exile": 1}

    def test_multi_word_name_with_qty(self):
        result = parse_card_list_or_names(["3 Path to Exile"])
        assert result == {"Path to Exile": 3}
