import pytest

from mtg_utils.utils.formats import BASIC_LANDS, FORMATS, FormatRules, validate_deck

COMMANDER = FORMATS["commander"]
PAUPER = FORMATS["pauper"]


def _basics(name: str, qty: int) -> dict[str, int]:
    return {name: qty}


@pytest.mark.unit
class TestFormatRules:
    def test_commander_rules(self):
        assert COMMANDER == FormatRules(main_size=100, main_size_exact=True, sideboard_max=0, max_copies=1)

    def test_pauper_rules(self):
        assert PAUPER == FormatRules(main_size=60, main_size_exact=False, sideboard_max=15, max_copies=4)

    def test_basic_lands_include_snow_covered(self):
        assert "Island" in BASIC_LANDS
        assert "Snow-Covered Island" in BASIC_LANDS
        assert "Wastes" in BASIC_LANDS


@pytest.mark.unit
class TestValidateDeck:
    def test_clean_pauper_deck_has_no_violations(self):
        main = {"Lightning Bolt": 4, "Mountain": 56}
        side = {"Pyroblast": 4, "Red Elemental Blast": 4, "Smash to Smithereens": 4, "Flaring Pain": 3}
        assert validate_deck(main, side, PAUPER) == []

    def test_clean_commander_deck_has_no_violations(self):
        main = {"Zada, Hedron Grinder": 1, "Mountain": 99}
        assert validate_deck(main, {}, COMMANDER) == []

    def test_pauper_mainboard_below_minimum(self):
        main = {"Mountain": 58}
        assert validate_deck(main, {}, PAUPER) == ["58 cards in mainboard (need at least 60)"]

    def test_pauper_mainboard_above_minimum_is_fine(self):
        main = {"Mountain": 61}
        assert validate_deck(main, {}, PAUPER) == []

    def test_commander_mainboard_not_exactly_100(self):
        main = {"Mountain": 101}
        assert validate_deck(main, {}, COMMANDER) == ["101 cards in mainboard (need exactly 100)"]

    def test_pauper_sideboard_above_maximum(self):
        main = {"Mountain": 60}
        side = {"Pyroblast": 4, "Red Elemental Blast": 4, "Smash to Smithereens": 4, "Flaring Pain": 4, "Plains": 1}
        assert validate_deck(main, side, PAUPER) == ["17 cards in sideboard (max 15)"]

    def test_pauper_too_many_copies_counts_sideboard(self):
        main = {"Lightning Bolt": 4, "Mountain": 56}
        side = {"Lightning Bolt": 1}
        assert validate_deck(main, side, PAUPER) == ["5x Lightning Bolt (max 4, counting sideboard)"]

    def test_commander_duplicate_nonbasic(self):
        main = {"Sol Ring": 2, "Mountain": 98}
        assert validate_deck(main, {}, COMMANDER) == ["2x Sol Ring (max 1, counting sideboard)"]

    def test_basic_lands_are_exempt_from_copy_limit(self):
        main = {"Snow-Covered Island": 30, "Island": 30}
        assert validate_deck(main, {}, PAUPER) == []

    def test_violations_are_sorted_by_card_name(self):
        main = {"Zap": 5, "Bolt": 5, "Mountain": 50}
        assert validate_deck(main, {}, PAUPER) == [
            "5x Bolt (max 4, counting sideboard)",
            "5x Zap (max 4, counting sideboard)",
        ]
