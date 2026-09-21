from rich.rule import Rule

from mtg_utils.commands.list_decks.logic import load_deck_cards
from mtg_utils.utils.console import console


def _render_cards(cards: dict[str, int]) -> None:
    for name, qty in sorted(cards.items(), key=lambda x: x[0]):
        console.print(f"[dim]{qty}[/dim] {name}")


def render_decklist_panel(alias: str, deck_file: str) -> None:
    """Render a single deck's card list with its alias as title.

    Args:
        alias: Deck alias from config
        deck_file: Path to the deck file
    """
    try:
        mainboard, sideboard = load_deck_cards(deck_file)
        if not mainboard and not sideboard:
            console.print(f"[bold bright_cyan]{alias}[/bold bright_cyan] (empty deck)")
            return

        header = f"[bold bright_cyan]{alias}[/bold bright_cyan] ({sum(mainboard.values())} cards"
        if sideboard:
            header += f" + {sum(sideboard.values())} sideboard"
        console.print(Rule(header + ")"))

        _render_cards(mainboard)
        if sideboard:
            console.print(Rule("[dim]Sideboard[/dim]", align="left"))
            _render_cards(sideboard)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Deck file not found: {deck_file}")


def render_decks_with_cards(decks: list[tuple[str, str]]) -> None:
    """Render multiple decks with their card contents.

    Args:
        decks: List of (alias, deck_file) tuples
    """
    if not decks:
        console.print("[yellow]No decks configured.[/yellow]")
        return

    console.print(Rule("[bold]Configured decks with card contents[/bold]"))

    # Render each deck
    for alias, deck_file in decks:
        render_decklist_panel(alias, deck_file)
        console.print("")
