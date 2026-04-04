import pytest
from rich.table import Table

from mtg_utils.utils.panels import card_table, panel_row, side_by_side


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
class TestPanelRow:
    def test_returns_rich_table(self):
        from rich.panel import Panel

        result = panel_row([Panel("a"), Panel("b"), Panel("c")])
        assert isinstance(result, Table)

    def test_column_count_matches_input(self):
        from rich.panel import Panel

        result = panel_row([Panel("a"), Panel("b"), Panel("c")])
        assert len(result.columns) == 3

    def test_single_panel(self):
        from rich.panel import Panel

        result = panel_row([Panel("x")])
        assert isinstance(result, Table)
        assert len(result.columns) == 1


@pytest.mark.unit
def test_side_by_side_returns_expandable_two_column_row():
    from rich.panel import Panel

    result = side_by_side(Panel("left"), Panel("right"))

    assert isinstance(result, Table)
    assert len(result.columns) == 2
    assert result.expand is True
