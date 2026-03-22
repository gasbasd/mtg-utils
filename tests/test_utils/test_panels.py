import pytest
from rich.table import Table

from mtg_utils.utils.panels import card_table, side_by_side


@pytest.mark.unit
class TestCardTable:
    def test_returns_rich_table(self):
        result = card_table([("Island", 2), ("Forest", 1)])
        assert isinstance(result, Table)

    def test_sorted_alphabetically(self):
        tbl = card_table([("Island", 3), ("Forest", 1)])
        assert tbl.row_count == 2

    def test_empty_list(self):
        tbl = card_table([])
        assert tbl.row_count == 0

    def test_row_style_accepted(self):
        """card_table(row_style=...) should not raise."""
        tbl = card_table([("Lightning Bolt", 4)], row_style="red")
        assert isinstance(tbl, Table)


@pytest.mark.unit
class TestSideBySide:
    def test_returns_rich_table(self):
        from rich.panel import Panel

        p1 = Panel("left")
        p2 = Panel("right")
        result = side_by_side(p1, p2)
        assert isinstance(result, Table)

    def test_has_two_columns(self):
        from rich.panel import Panel

        result = side_by_side(Panel("a"), Panel("b"))
        assert len(result.columns) == 2
