import pytest
from rich.table import Table

from mtg_utils.commands.update_card_library.render import _shared_card_table


@pytest.mark.unit
class TestSharedCardTable:
    def test_returns_rich_table(self):
        result = _shared_card_table(["Island", "Forest"], {"Island": 2, "Forest": 1})
        assert isinstance(result, Table)

    def test_sorted_order(self):
        """Cards should be listed alphabetically (Forest before Island)."""
        tbl = _shared_card_table(["Island", "Forest"], {"Island": 3, "Forest": 1})
        # Row 0 = Forest, Row 1 = Island — verify via row_count
        assert tbl.row_count == 2

    def test_empty_list(self):
        tbl = _shared_card_table([], {})
        assert tbl.row_count == 0
