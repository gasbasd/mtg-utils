

import json
import os
from pathlib import Path
DEFAULT_CONFIG_FILE = "config.json"

def load_config(config_file: str = DEFAULT_CONFIG_FILE) -> dict:
    """Load the configuration from JSON file."""
    config_path = Path(config_file)

    if not config_path.exists():
        # Create default config file if it doesn't exist
        default_config = {
            "binder_id": "vw7sTSczsUaDX1K9FO5tgg",
            "decks": {
                "example_deck": {
                    "id": "MvFOpMknJUKUnL6BMoQv6w",
                    "file": "decks/example_deck.txt"
                }
            },
            "purchased_file": "card_library/purchased.txt"
        }
        # Ensure directory exists
        os.makedirs(config_path.parent, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default config file: {config_file}")
        return default_config

    with open(config_path, 'r') as f:
        return json.load(f)
