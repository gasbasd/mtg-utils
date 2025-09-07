import logging

import click

from mtg_utils.commands.compare_decks import compare_decks
from mtg_utils.commands.check_missing_cards import check_missing_cards
from mtg_utils.commands.update_card_library import update_card_library


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


cli.add_command(compare_decks)
cli.add_command(check_missing_cards)
cli.add_command(update_card_library)

if __name__ == "__main__":
    cli()
