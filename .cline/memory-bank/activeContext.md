# Active Context

## Current State

The mtg-utils project is actively maintained with the following structure:

- **Core Package**: `mtg_utils/` - Main Python package
- **Test Suite**: `tests/` - pytest-based tests (154 tests passing)
- **Configuration**: `config.json` - User configuration (not committed)
- **Data Directory**: `card_library/` - Runtime-generated data (not committed)

---

## Recent Changes (Current Session)

### List Decks Command Refactoring

The `list-decks` command has been completely refactored to:

1. **Follow Modular Architecture**: Now uses the same pattern as `update_card_library`
   - `mtg_utils/commands/list_decks/command.py` - CLI wrapper
   - `mtg_utils/commands/list_decks/logic.py` - Deck loading logic
   - `mtg_utils/commands/list_decks/render.py` - Rich-based rendering

2. **Print Decklists**: Now displays actual card contents for each deck
   - Shows deck alias with card count (e.g., `gretchen (100 cards)`)
   - Displays all cards sorted alphabetically
   - Prints empty line separation between decks

3. **Reused Rendering Logic**: Created new `mtg_utils/utils/decklists.py` module
   - `render_decklist()` - Render a single deck's card list
   - `render_multiple_decks()` - Render multiple decklists side-by-side

### Removed Old Files

- `mtg_utils/commands/list_decks.py` - Replaced with modular structure

### Test Updates

- Added tests: `tests/test_commands/test_list_decks/` (command, logic, render)
- Added tests: `tests/test_utils/test_decklists.py`
- Updated: `tests/test_list_decks.py`
- **154 tests passing** with 100.00% coverage

---

## Next Steps

1. Review and approve current changes
2. Consider committing modular command structure pattern to future tasks
3. Continue expanding command functionality as needed

---

## Active Decisions & Considerations

- Using Poetry as package manager for dependency management
- CLI built with Click for user-friendly interface
- Rich library for beautiful console output
- Pydantic for data validation
- 100% test coverage target (currently achieved: 100.00%)
- Modular command structure for maintainability

---

## Important Patterns & Preferences

1. **Modular Command Structure**: Each CLI command has its own directory with `command.py`, `logic.py`, and `render.py` files
2. **Separation of Concerns**: CLI wrapper, business logic, and console output are separated
3. **Reused Logic**: Common functionality moved to `utils/` modules
4. **Consistent Documentation**: All public functions need docstrings
5. **Type Hints**: Required for all function signatures
6. **Commands don't import from other commands**: Each command is self-contained

---

## Learnings & Project Insights

- The project follows PEP 8 with a 120 character line limit
- Configuration is loaded from `config.json` using Pydantic models
- Moxfield API integration is done via the `moxfield_api.py` module
- Card files are stored in `card_library/` directory
- Test coverage can be slightly below 100% when coverage lines are in error/warning scenarios that are hard to test
