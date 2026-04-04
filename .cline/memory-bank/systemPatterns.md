# System Patterns

## System Architecture

```
mtg-utils/
├── mtg_utils/              # Main package
│   ├── __init__.py
│   ├── main.py            # CLI entry point with Click
│   ├── commands/          # CLI command modules
│   │   ├── __init__.py
│   │   └── [command]/
│   │       ├── __init__.py
│   │       ├── command.py # CLI wrapper with Click decorators
│   │       ├── logic.py   # Business logic
│   │       └── render.py  # Console output with Rich
│   └── utils/             # Shared utilities
│       ├── __init__.py
│       ├── cards.py       # Card data models and processing
│       ├── config.py      # Configuration loading with Pydantic
│       ├── console.py     # Rich console setup
│       ├── decklists.py   # Decklist rendering (NEW)
│       ├── moxfield_api.py# Moxfield API integration
│       ├── panels.py      # Console panel rendering
│       └── readers.py     # File reading utilities
├── tests/                 # Test suite
│   ├── conftest.py        # Shared fixtures
│   └── test_*.py          # Individual test files
├── card_library/          # Data directory (runtime-generated)
│   ├── owned_cards.txt
│   ├── available_cards.txt
│   ├── purchased.txt
│   └── decks/
├── config.json            # User configuration (not committed)
└── pyproject.toml         # Poetry configuration
```

## Key Technical Decisions

1. **Modular Command Structure**: Each CLI command is self-contained with its own directory
2. **Separation of Concerns**: CLI wrapper (`command.py`), logic (`logic.py`), and rendering (`render.py`) are separated
3. **Configuration Management**: Pydantic models for type-safe configuration loading
4. **Console Output**: Rich library for formatted tables, panels, and progress indicators
5. **Reused Logic**: Common functionality extracted to `utils/` modules
6. **Commands don't import from other commands**: Each command is independent

## Design Patterns in Use

1. **Command Pattern**: Each CLI command is a separate module
2. **Factory Pattern**: Configuration loading uses Pydantic's model validation
3. **Module Pattern**: Shared utilities are organized in `mtg_utils.utils`

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (main.py)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │Command1│      │Command2│      │CommandN│
    └────┬───┘      └────┬───┘      └────┬───┘
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  Logic  │    │  Logic  │    │  Logic  │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  Render │    │  Render │    │  Render │
    └─────────┘    └─────────┘    └─────────┘
```

## Critical Implementation Paths

1. **CLI Request Flow**: User runs command → Click parses args → command.py calls logic.py → logic.py processes → render.py formats output
2. **Configuration Loading**: `load_config()` → Pydantic validation → Config object passed to logic
3. **Moxfield API**: `get_binder_cards()` → Cloudscraper bypass → JSON parsing → Card list
4. **Decklist Rendering**: Deck file read → `parse_card_list()` → `render_decklist()` → Rich Panel output

## Configuration Structure

```json
{
  "binder_id": "moxfield-binder-id",
  "decks": {
    "deck_name": {
      "file": "card_library/decks/deck_name.txt",
      "id": "moxfield-deck-id"
    }
  },
  "purchased_file": "card_library/purchased.txt"
}
