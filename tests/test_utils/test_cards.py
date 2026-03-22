import pytest

from mtg_utils.utils.cards import parse_card_list


@pytest.mark.unit
class TestParseCardList:
    def test_empty_list(self):
        assert parse_card_list([]) == {}

    def test_single_entry(self):
        assert parse_card_list(["1 Island"]) == {"Island": 1}

    def test_multiple_copies(self):
        assert parse_card_list(["4 Lightning Bolt"]) == {"Lightning Bolt": 4}

    def test_multi_word_name(self):
        assert parse_card_list(["2 Birds of Paradise"]) == {"Birds of Paradise": 2}

    def test_multiple_entries(self):
        result = parse_card_list(["3 Island", "1 Forest", "2 Mountain"])
        assert result == {"Island": 3, "Forest": 1, "Mountain": 2}
