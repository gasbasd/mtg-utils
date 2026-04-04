---
description: Overview of mtg-utils project architecture, directory structure, and technology stack
author: Simone Gasbarroni
version: 1.0
tags: ["project-overview", "architecture", "python"]
---

# mtg-utils Project Overview

## Objective

mtg-utils is a command-line utility designed for managing Magic: The Gathering card collections, decks, and performing various analyses. It helps users track their card collections from Moxfield, manage multiple decks, check missing cards, and monitor newly purchased cards.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Python Version | >=3.13 |
| Package Manager | Poetry |
| CLI Framework | Click |
| HTTP Requests | Requests + Cloudscraper |
| Data Validation | Pydantic |
| Console Output | Rich |
| Testing | pytest + pytest-cov |
| Linting | Ruff + Pyright |

---

## Directory Structure

```
mtg-utils/
├── mtg_utils/               # Main package
│   ├── __init__.py
│   ├── main.py             # CLI entry point with Click
│   ├── commands/           # CLI command modules
│   │   ├── __init__.py
│   │   ├── compare_decks.py
│   │   ├── list_decks.py
│   │   └── check_missing_cards/
│   │   │   ├── __init__.py
│   │   │   ├── command.py  # CLI command wrapper
│   │   │   ├── logic.py    # Business logic
│   │   │   └── render.py   # Console output
│   │   └── update_card_library/
│   │       ├── __init__.py
│   │       ├── command.py
│   │       ├── logic.py
│   │       └── render.py
│   └── utils/              # Shared utilities
│       ├── __init__.py
│       ├── cards.py        # Card data models and processing
│       ├── config.py       # Configuration loading
│       ├── console.py      # Rich console setup
│       ├── moxfield_api.py # Moxfield API integration
│       ├── panels.py       # Console panel rendering
│       └── readers.py      # File reading utilities
├── tests/                  # Test suite
├── card_library/           # Data directory (generated at runtime)
│   ├── owned_cards.txt
│   ├── available_cards.txt
│   ├── purchased.txt
│   ├── purchased_formatted.txt
│   └── decks/
├── config.json             # User configuration
├── pyproject.toml          # Poetry configuration
├── .clinerules/            # AI assistant rules
└── README.md
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mtg-utils update-library` | Update card collection and decks from Moxfield |
| `mtg-utils check-missing-cards` | Check missing cards for a deck |
| `mtg-utils compare-decks` | Compare two decks for card differences |
| `mtg-utils list-decks` | List configured decks |

---

## Core Concepts

### Card Library

The `card_library/` directory stores all card data:

- `owned_cards.txt` - Your complete Moxfield collection
- `available_cards.txt` - Cards available (owned + purchased - used)
- `purchased.txt` - Recently purchased cards
- `decks/` - Individual decklist files

### Configuration

Users configure the tool via `config.json`:

```json
{
  "binder_id": "your-moxfield-binder-id",
  "decks": {
    "deck1": {
      "file": "card_library/decks/deck1.txt",
      "id": "moxfield-deck-id-1"
    }
  },
  "purchased_file": "card_library/purchased.txt"
}
```

---

## Development Setup

### Prerequisites

- Python 3.13+
- Poetry (recommended) or virtualenv

### Installation (Poetry)

```bash
git clone https://github.com/yourusername/mtg-utils.git
cd mtg-utils
poetry install
poetry shell
```

### Running Tests

```bash
poetry run pytest
```

### Linting

```bash
poetry run ruff check .
poetry run pyright
