import click

from mtg_utils.commands.list_decks.render import render_decks_with_cards
from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import console


@click.command()
@click.option("--config-file", default=DEFAULT_CONFIG_FILE, help="Path to config file")
def list_decks(config_file: str) -> None:
    """List all configured decks with their card contents."""
    config = load_config(config_file)
    decks = sorted(config.decks.items())

    if not decks:
        console.print("[yellow]No decks configured.[/yellow]")
        return

    render_decks_with_cards([(alias, deck.file) for alias, deck in decks])
