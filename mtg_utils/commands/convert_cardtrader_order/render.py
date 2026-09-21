from decimal import Decimal

from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from mtg_utils.utils.console import console
from mtg_utils.utils.panels import side_by_side


def _breakdown_text(counts: dict[str, int]) -> str:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return " · ".join(f"{escape(value)} {count}" for value, count in ordered)


def _summary_panel(converted: list[dict[str, str]], breakdown: dict[str, dict[str, int]], total: Decimal) -> Panel:
    summary = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    summary.add_column("label", style="dim")
    summary.add_column("value")
    summary.add_row("cards", str(len(converted)))
    summary.add_row("unique names", str(len({entry["Name"] for entry in converted})))
    summary.add_row("foils", str(breakdown["Foil"].get("foil", 0)))
    summary.add_row("total", f"€{total:.2f}")
    summary.add_row("conditions", _breakdown_text(breakdown["Condition"]))
    summary.add_row("languages", _breakdown_text(breakdown["Language"]))
    return Panel(summary, title=f"Converted: {len(converted)}", border_style="green")


def _list_panel(title: str, entries: list[str], border_style: str) -> Panel:
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column("entry")
    for entry in entries:
        table.add_row(escape(entry))
    return Panel(table, title=title, border_style=border_style)


def _corrections_panel(corrections: list[dict[str, str]]) -> Panel:
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column("before", style="dim")
    table.add_column("arrow", style="dim")
    table.add_column("after", style="cyan")
    for correction in corrections:
        table.add_row(escape(correction["before"]), "→", escape(correction["after"]))
    return Panel(table, title=f"Corrected: {len(corrections)}", border_style="cyan")


def render_conversion(
    converted: list[dict[str, str]],
    skipped: list[str],
    corrections: list[dict[str, str]],
    unresolved: list[str],
    breakdown: dict[str, dict[str, int]],
    output_file: str,
    notice: str | None = None,
) -> None:
    total = sum((Decimal(entry["Purchase Price"]) for entry in converted), Decimal(0))

    console.print(Rule(f"[bold]CardTrader → Moxfield: {len(converted)} cards · €{total:.2f}[/bold]"))

    summary_panel = _summary_panel(converted, breakdown, total)
    if skipped:
        console.print(side_by_side(summary_panel, _list_panel(f"Skipped, not Magic: {len(skipped)}", skipped, "yellow")))
    else:
        console.print(summary_panel)

    if corrections:
        console.print(_corrections_panel(corrections))

    if unresolved:
        console.print(
            _list_panel(f"Not found on Scryfall, check by hand: {len(unresolved)}", unresolved, "red")
        )

    if notice:
        console.print(f"[yellow]⚠[/yellow] {escape(notice)}")

    console.print(f"[green]✓[/green] Wrote {escape(output_file)}")
