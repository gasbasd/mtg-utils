---
description: CLI command patterns and workflow guidelines for mtg-utils Click-based commands
author: Simone Gasbarroni
version: 1.0
tags: ["cli", "click", "workflows"]
---

# CLI Workflows

## Click CLI Pattern

mtg-utils uses Click for building command-line interfaces. This document outlines the patterns and best practices for creating and modifying CLI commands.

---

## Directory Structure

```
mtg_utils/
└── commands/
    ├── __init__.py
    ├── check_missing_cards/
    │   ├── __init__.py
    │   ├── command.py  # CLI command wrapper with Click decorators
    │   ├── logic.py    # Business logic
    │   └── render.py   # Console output
    └── update_card_library/
        ├── __init__.py
        ├── command.py
        ├── logic.py
        └── render.py
```

---

## Command Structure

Each command follows a modular pattern:

### 1. `command.py` - CLI Wrapper

Contains the Click command definition with decorators and option parsing.

```python
import click
from rich.console import Console
from mtg_utils.utils.console import console

@click.command()
@click.option("--deck-file", "-f", help="Path to decklist file")
@click.option("--moxfield-id", "-m", help="Moxfield deck ID")
def check_missing_cards(deck_file: str | None, moxfield_id: str | None):
    """
    Check which cards are missing from your collection.
    """
    # Parse options and call logic
    pass
```

### 2. `logic.py` - Business Logic

Contains pure logic for processing and calculations.

```python
from mtg_utils.utils.moxfield_api import get_binder_cards
from mtg_utils.utils.readers import read_deck_list

def get_missing_cards(deck_file: str, binder_cards: list[str]) -> list[str]:
    """Get list of cards missing from binder collection."""
    deck_cards = read_deck_list(deck_file)
    return [card for card in deck_cards if card not in binder_cards]
```

### 3. `render.py` - Console Output

Contains Rich-based rendering for formatted output.

```python
from rich.table import Table
from mtg_utils.utils.console import console

def render_missing_cards(cards: list[str]) -> None:
    """Render missing cards table."""
    table = Table(title="Missing Cards")
    table.add_column("Card Name", style="cyan")
    for card in cards:
        table.add_row(card)
    console.print(table)
```

---

## Adding a New Command

1. Create a new directory under `mtg_utils/commands/`
2. Create `__init__.py`, `command.py`, `logic.py`, and `render.py`
3. Add the command to `mtg_utils/main.py` using `cli.add_command()`
4. Write tests in `tests/test_commands/test_<command_name>.py`

---

## Environment Variables

Use Click's `envvar` parameter for environment variable support:

```python
@click.option(
    "--debug",
    envvar="DEBUG",
    default=False,
    type=bool,
    is_flag=True,
    help="Debug mode: set logging level to DEBUG",
)
```

---

## Error Handling

Always use `console.print()` for error messages:

```python
# ✅ GOOD
console.print(f"[bold red]Error:[/bold red] Deck file not found: {path}")

# ❌ BAD
print(f"Error: Deck file not found: {path}")
