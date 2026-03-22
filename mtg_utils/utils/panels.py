from rich.markup import escape
from rich.table import Table


def card_table(cards: list[tuple[str, int]], row_style: str = "") -> Table:
    """Build a standard Rich Table for a card list sorted alphabetically."""
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column("qty", justify="right", style="dim")
    table.add_column("name", style=row_style)
    for card, qty in sorted(cards, key=lambda x: x[0]):
        table.add_row(str(qty), escape(card))
    return table


def side_by_side(left, right) -> Table:
    """Render two Rich renderables side-by-side in equal-width columns."""
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(left, right)
    return grid
