---
description: Python coding standards and best practices for mtg-utils
author: Simone Gasbarroni
version: 1.0
tags: ["coding-standards", "python", "style-guide"]
---

# Coding Standards

## Python Style Guidelines

This document outlines the coding standards for the mtg-utils project. Following these guidelines ensures consistent, maintainable code across the project.

---

## Style Requirements

### Code Style

- **PEP 8 compliance** is required for all Python code
- **Line length**: Maximum 120 characters (configured in `ruff`)
- **Indentation**: 4 spaces per indentation level
- **String quotes**: Use double quotes `"` for consistency

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Functions/Methods | snake_case | `check_missing_cards` |
| Classes | PascalCase | `CardLibrary` |
| Variables | snake_case | `deck_list` |
| Constants | UPPER_SNAKE_CASE | `MAX_DECK_SIZE` |
| Modules | snake_case | `moxfield_api.py` |

### Imports

Imports should be organized in the following order:

1. Standard library imports
2. Third-party imports (e.g., click, rich, requests)
3. Local project imports

```python
# Standard library
import os
import json

# Third-party
import click
from rich.console import Console

# Local project
from mtg_utils.utils.console import console
```

---

## Type Hints

Type hints are **required** for all function signatures:

```python
# ✅ GOOD
def check_missing_cards(deck_file: str, binder_cards: list[str]) -> list[str]:
    pass

# ❌ BAD
def check_missing_cards(deck_file, binder_cards):
    pass
```

### Type Hint Rules

- Always specify parameter types
- Always specify return type (use `-> None` for functions that don't return)
- Use `list[str]`, `dict[str, Any]`, etc. for generic types
- Use `Optional[T]` for nullable types

---

## Docstrings

All public functions, classes, and modules should have docstrings:

```python
def check_missing_cards(deck_file: str, binder_cards: list[str]) -> list[str]:
    """
    Check which cards are missing from the binder collection.

    Args:
        deck_file: Path to the decklist file
        binder_cards: List of cards in the binder collection

    Returns:
        List of card names that are missing
    """
    pass
```

---

## Error Handling

- Use specific exception types when possible
- Provide meaningful error messages
- Handle file I/O errors gracefully

```python
# ✅ GOOD
def read_deck_list(path: str) -> list[str]:
    try:
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Deck file not found: {path}")
        raise

# ❌ BAD
def read_deck_list(path: str) -> list[str]:
    with open(path, 'r') as f:
        return f.readlines()
```

---

## Console Output

Use the `rich` library for formatted console output:

```python
from rich.console import Console
from rich.table import Table
from mtg_utils.utils.console import console

# Use console.print() instead of print()
console.print("[bold green]Success![/bold green]")

# Use rich formatting for tables and panels
table = Table(title="Deck Comparison")
table.add_column("Card", style="cyan")
table.add_column("Count", style="magenta")
```

---

## Configuration

Configuration is loaded from `config.json` using Pydantic models:

```python
from mtg_utils.utils.config import Config, DeckConfig

# Load configuration
config = Config.from_file("config.json")

# Access configuration
for name, deck in config.decks.items():
    console.print(f"Deck: {name}")
```

---

## File I/O

- Use `with open()` for all file operations
- Prefer text mode for card files
- Handle encoding explicitly (UTF-8)

```python
# ✅ GOOD
def write_card_list(path: str, cards: list[str]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(cards)))

# ❌ BAD
open('file.txt', 'w').write(cards)
