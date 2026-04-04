from rich.rule import Rule

from mtg_utils.commands.list_decks.logic import load_deck_cards
from mtg_utils.utils.console import console


def render_decklist_panel(alias: str, deck_file: str) -> None:
    """Render a single deck's card list with its alias as title.

    Args:
        alias: Deck alias from config
        deck_file: Path to the deck file
    """
    try:
        cards = load_deck_cards(deck_file)
        if not cards:
            console.print(f"[bold bright_cyan]{alias}[/bold bright_cyan] (empty deck)")
            return

        total_cards = sum(cards.values())
        console.print(Rule(f"[bold bright_cyan]{alias}[/bold bright_cyan] ({total_cards} cards)"))

        # Sort cards alphabetically and render
        card_items = sorted(cards.items(), key=lambda x: x[0])
        for name, qty in card_items:
            console.print(f"[dim]{qty}[/dim] {name}")
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
