import pytest

from mtg_utils.utils.cards import SIDEBOARD_MARKER, parse_card_list, parse_card_list_or_names, split_boards


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

    def test_repeated_entries_accumulate(self):
        # A hand-written list may split copies of one card across several lines.
        assert parse_card_list(["4 Lightning Bolt", "2 Lightning Bolt"]) == {"Lightning Bolt": 6}

    def test_comment_lines_are_skipped(self):
        assert parse_card_list(["1 Island", "# Sideboard", "2 Forest"]) == {"Island": 1, "Forest": 2}


@pytest.mark.unit
class TestParseCardListOrNames:
    def test_comment_lines_are_skipped(self):
        assert parse_card_list_or_names(["Island", "# Sideboard", "2 Forest"]) == {"Island": 1, "Forest": 2}


@pytest.mark.unit
class TestSplitBoards:
    def test_no_marker_is_all_mainboard(self):
        assert split_boards(["1 Island", "2 Forest"]) == (["1 Island", "2 Forest"], [])

    def test_marker_splits_boards(self):
        lines = ["1 Island", SIDEBOARD_MARKER, "2 Forest", "1 Plains"]
        assert split_boards(lines) == (["1 Island"], ["2 Forest", "1 Plains"])

    def test_marker_is_case_insensitive(self):
        assert split_boards(["1 Island", "# sideboard", "2 Forest"]) == (["1 Island"], ["2 Forest"])

    def test_empty_list(self):
        assert split_boards([]) == ([], [])
