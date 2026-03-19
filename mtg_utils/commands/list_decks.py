import click

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config


@click.command()
@click.option("--config-file", default=DEFAULT_CONFIG_FILE, help="Path to config file")
def list_decks(config_file: str) -> None:
    """List all configured decks and their file paths."""
    config = load_config(config_file)
    for alias, deck in sorted(config["decks"].items()):
        print(f"{alias}\t{deck['file']}")
