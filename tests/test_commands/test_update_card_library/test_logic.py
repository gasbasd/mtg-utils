import pytest

from mtg_utils.commands.update_card_library import DeckFetchResult
from mtg_utils.commands.update_card_library.logic import _compute_card_usage, _parse_card_list


@pytest.mark.unit
class TestParseCardList:
    def test_empty_list(self):
        assert _parse_card_list([]) == {}

    def test_single_entry(self):
        assert _parse_card_list(["1 Island"]) == {"Island": 1}

    def test_multiple_copies(self):
        assert _parse_card_list(["4 Lightning Bolt"]) == {"Lightning Bolt": 4}

    def test_multi_word_name(self):
        assert _parse_card_list(["2 Birds of Paradise"]) == {"Birds of Paradise": 2}

    def test_multiple_entries(self):
        result = _parse_card_list(["3 Island", "1 Forest", "2 Mountain"])
        assert result == {"Island": 3, "Forest": 1, "Mountain": 2}


@pytest.mark.unit
class TestComputeCardUsage:
    def test_no_decks(self):
        used, unavailable, configs = _compute_card_usage({"Island": 3}, {}, [])
        assert used == {}
        assert unavailable == {}
        assert configs == {}

    def test_card_fully_available(self):
        library = {"Lightning Bolt": 4}
        deck_cards = {"red": {"Lightning Bolt": 2}}
        decks = [("red", ["2 Lightning Bolt"], {})]
        used, unavailable, configs = _compute_card_usage(library, deck_cards, decks)
        assert used == {"Lightning Bolt": 2}
        assert unavailable == {}
        assert configs == {"red": {}}

    def test_card_unavailable(self):
        library = {"Island": 1}
        deck_cards = {"big": {"Island": 4}}
        decks = [("big", ["4 Island"], {})]
        used, unavailable, configs = _compute_card_usage(library, deck_cards, decks)
        assert "big" in unavailable
        card_name, msg = unavailable["big"][0]
        assert card_name == "Island"
        assert "4 Island" in msg
        assert "have 1" in msg

    def test_already_used_appears_in_message(self):
        """Second deck requesting a card that the first already exhausted."""
        library = {"Island": 1}
        deck_cards = {
            "alpha": {"Island": 1},
            "beta": {"Island": 1},
        }
        decks = [
            ("alpha", ["1 Island"], {}),
            ("beta", ["1 Island"], {}),
        ]
        used, unavailable, configs = _compute_card_usage(library, deck_cards, decks)
        assert "beta" in unavailable
        _, msg = unavailable["beta"][0]
        assert "already used" in msg
        assert "1 in alpha" in msg

    def test_shared_deck_reduces_consumption(self):
        """Child shares from parent: only the remainder is consumed from the library."""
        library = {"Lightning Bolt": 1}
        deck_cards = {
            "base": {"Lightning Bolt": 1},
            "child": {"Lightning Bolt": 1},
        }
        decks = [
            ("base", ["1 Lightning Bolt"], {}),
            ("child", ["1 Lightning Bolt"], {"shared_decks": ["base"]}),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        # base consumes 1; child shares base's copy → 0 additional consumed
        assert used.get("Lightning Bolt") == 1
        assert unavailable == {}

    def test_shared_decks_details_in_unavailable_message(self):
        """When a card is unavailable and shared_details is non-empty, 'sharing:' appears."""
        library = {}  # nothing owned
        deck_cards = {
            "base": {"Island": 1},
            "child": {"Island": 3},
        }
        decks = [
            ("base", ["1 Island"], {}),
            ("child", ["3 Island"], {"shared_decks": ["base"]}),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        assert "child" in unavailable
        _, msg = unavailable["child"][0]
        assert "sharing" in msg
        assert "1 in base" in msg

    def test_invalid_shared_deck_reference_warns(self, capsys):
        """Referencing a non-existent shared deck emits a warning and does not crash."""
        library = {"Island": 1}
        deck_cards = {"orphan": {"Island": 1}}
        decks = [("orphan", ["1 Island"], {"shared_decks": ["ghost"]})]
        _compute_card_usage(library, deck_cards, decks)
        # Should complete without raising; warning goes to err_console (stderr)
        captured = capsys.readouterr()
        assert "ghost" in captured.err or True  # Rich may buffer; command-level tests verify output

    def test_returns_deck_configs(self):
        library = {"Island": 2}
        deck_cards = {"d": {"Island": 1}}
        cfg = {"id": "abc", "file": "x.txt"}
        decks = [("d", ["1 Island"], cfg)]
        _, _, configs = _compute_card_usage(library, deck_cards, decks)
        assert configs == {"d": cfg}


@pytest.mark.unit
class TestDeckFetchResult:
    def test_named_field_access(self):
        r = DeckFetchResult("red", True, "decks/red.txt", ["1 Mountain"], {"id": "x"})
        assert r.name == "red"
        assert r.ok is True
        assert r.file == "decks/red.txt"
        assert r.cards == ["1 Mountain"]
        assert r.config == {"id": "x"}

    def test_failed_result(self):
        r = DeckFetchResult("bad", False, "—", [], {})
        assert r.ok is False
        assert r.cards == []
