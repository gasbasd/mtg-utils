import logging

import click
from rich.rule import Rule

from mtg_utils.commands.check_missing_cards import check_missing_cards
from mtg_utils.commands.compare_decks import compare_decks
from mtg_utils.commands.list_decks import list_decks
from mtg_utils.commands.show_shopping_list import show_shopping_list
from mtg_utils.commands.update_card_library import update_card_library
from mtg_utils.utils.console import console


@click.group()
@click.version_option()
@click.option(
    "--debug",
    envvar="DEBUG",
    default=False,
    type=bool,
    is_flag=True,
    help="Debug mode: set logging level to DEBUG",
)
def cli(debug: bool = False):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    console.print(Rule("[bold green]🃏  mtg-utils[/bold green]"))


cli.add_command(compare_decks)
cli.add_command(check_missing_cards)
cli.add_command(list_decks)
cli.add_command(show_shopping_list)
cli.add_command(update_card_library)

if __name__ == "__main__":
    cli()
