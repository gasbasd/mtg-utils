import pytest

from mtg_utils.commands.update_card_library import DeckFetchResult
from mtg_utils.commands.update_card_library.logic import _compute_card_usage
from mtg_utils.utils.config import DeckConfig


def _deck_cfg(
    id: str = "fake",
    file: str = "fake.txt",
    shared_decks: list[str] | None = None,
) -> DeckConfig:
    return DeckConfig(id=id, file=file, shared_decks=shared_decks or [])


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
        cfg = _deck_cfg()
        decks = [("red", ["2 Lightning Bolt"], cfg)]
        used, unavailable, configs = _compute_card_usage(library, deck_cards, decks)
        assert used == {"Lightning Bolt": 2}
        assert unavailable == {}
        assert configs == {"red": cfg}

    def test_card_unavailable(self):
        library = {"Island": 1}
        deck_cards = {"big": {"Island": 4}}
        decks = [("big", ["4 Island"], _deck_cfg())]
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
            ("alpha", ["1 Island"], _deck_cfg()),
            ("beta", ["1 Island"], _deck_cfg()),
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
            ("base", ["1 Lightning Bolt"], _deck_cfg()),
            ("child", ["1 Lightning Bolt"], _deck_cfg(shared_decks=["base"])),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        # base consumes 1; child shares base's copy → 0 additional consumed
        assert used.get("Lightning Bolt") == 1
        assert unavailable == {}

    def test_overlapping_shared_decks_incremental_counting(self):
        """Regression: overlapping shared dependencies must not over/under-count reusable cards."""
        library = {"Snow-Covered Island": 16}
        deck_cards = {
            "gretchen": {"Snow-Covered Island": 14},
            "weavers": {"Snow-Covered Island": 12},
            "tatyova": {"Snow-Covered Island": 16},
        }
        decks = [
            ("gretchen", ["14 Snow-Covered Island"], _deck_cfg()),
            ("weavers", ["12 Snow-Covered Island"], _deck_cfg(shared_decks=["gretchen"])),
            (
                "tatyova",
                ["16 Snow-Covered Island"],
                _deck_cfg(shared_decks=["gretchen", "weavers"]),
            ),
        ]

        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)

        # Expected consumption: gretchen=14, weavers=0 (fully shared), tatyova=2 (16-14).
        assert used == {"Snow-Covered Island": 16}
        assert "tatyova" not in unavailable

    def test_shared_decks_details_in_unavailable_message(self):
        """When a card is unavailable and shared_details is non-empty, 'sharing:' appears."""
        library = {}  # nothing owned
        deck_cards = {
            "base": {"Island": 1},
            "child": {"Island": 3},
        }
        decks = [
            ("base", ["1 Island"], _deck_cfg()),
            ("child", ["3 Island"], _deck_cfg(shared_decks=["base"])),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        assert "child" in unavailable
        _, msg = unavailable["child"][0]
        assert "sharing" in msg
        assert "1 in base" in msg

    def test_returns_deck_configs(self):
        library = {"Island": 2}
        deck_cards = {"d": {"Island": 1}}
        cfg = DeckConfig(id="abc", file="x.txt")
        decks = [("d", ["1 Island"], cfg)]
        _, _, configs = _compute_card_usage(library, deck_cards, decks)
        assert configs == {"d": cfg}


@pytest.mark.unit
class TestDeckFetchResult:
    def test_named_field_access(self):
        r = DeckFetchResult("red", True, "decks/red.txt", ["1 Mountain"], _deck_cfg())
        assert r.name == "red"
        assert r.ok is True
        assert r.file == "decks/red.txt"
        assert r.cards == ["1 Mountain"]

    def test_failed_result(self):
        r = DeckFetchResult("bad", False, "—", [], _deck_cfg())
        assert r.ok is False
        assert r.cards == []

    def test_circular_shared_deck_reference(self):
        """Test circular shared deck detection: A shares from B, B shares from A."""
        library = {"Island": 10}
        deck_cards = {
            "alpha": {"Island": 5},
            "beta": {"Island": 5},
        }
        # Create circular reference: alpha -> beta -> alpha
        decks = [
            ("alpha", ["5 Island"], _deck_cfg(shared_decks=["beta"])),
            ("beta", ["5 Island"], _deck_cfg(shared_decks=["alpha"])),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        # Both should be able to share, but circular ref should be handled
        assert "alpha" not in unavailable
        assert "beta" not in unavailable

    def test_zero_quantity_in_shared_deck(self):
        """Test that a deck with 0 copies of a card doesn't break sharing."""
        library = {"Mountain": 2}
        deck_cards = {
            "base": {"Mountain": 0},  # 0 copies of the card
            "child": {"Mountain": 2},
        }
        decks = [
            ("base", ["0 Mountain"], _deck_cfg()),  # 0 quantity deck
            ("child", ["2 Mountain"], _deck_cfg(shared_decks=["base"])),
        ]
        used, unavailable, _ = _compute_card_usage(library, deck_cards, decks)
        # Child should use both from library since base has 0
        assert used == {"Mountain": 2}
        assert unavailable == {}
