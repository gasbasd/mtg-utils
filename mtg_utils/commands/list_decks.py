import click
from rich.table import Table

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import console


@click.command()
@click.option("--config-file", default=DEFAULT_CONFIG_FILE, help="Path to config file")
def list_decks(config_file: str) -> None:
    """List all configured decks and their file paths."""
    config = load_config(config_file)
    decks = sorted(config["decks"].items())
    if not decks:
        return
    table = Table(box=None, show_header=True, header_style="bold green")
    table.add_column("Alias")
    table.add_column("File", overflow="fold")
    for alias, deck in decks:
        table.add_row(alias, deck["file"])
    console.print(table)
