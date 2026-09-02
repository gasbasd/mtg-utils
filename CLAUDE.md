# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
poetry install                # install deps
poetry run mtg-utils --help   # run the CLI

make test        # fast inner-loop run: pytest -v -p no:cov
make lint        # ruff check mtg_utils tests
make typecheck   # pyright (checks mtg_utils only)
make coverage    # pytest + coverage; FAILS below 100%
make ci          # lint + typecheck + coverage — mirrors .github/workflows/ci.yml
make install-hooks  # copies .githooks/pre-commit (lint + typecheck) into .git/hooks
```

Running a subset:

```sh
poetry run pytest tests/test_commands/test_show_shopping_list/test_logic.py
poetry run pytest "tests/test_utils/test_panels.py::TestCardTable::test_sorted_alphabetically"
poetry run pytest -m unit          # or: -m integration
```

Coverage is only meaningful on the whole suite — `fail_under = 100` will trip on any subset.

Dev interpreter is Python 3.14.5 (pyenv venv named in the gitignored `.python-version`); pyright and CI target 3.14, while `requires-python` stays `>=3.13`.

## Working agreements

- **Test-first.** Write the failing test, then the implementation.
- **`make ci` must be green** before any change is called done. Coverage is enforced at 100%.
- **Never run `update-card-library`.** It calls the Moxfield API and rewrites `card_library/` wholesale. Exercise that code path through tests with `tmp_path` fixtures instead, and don't commit `card_library/` churn.
- **Conventional commits** (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) and `feature/`, `fix/`, `docs/` branch names.

## Architecture

### Command anatomy

Each command is a package under `mtg_utils/commands/<name>/` split three ways — this separation is the load-bearing convention of the codebase:

| File | Responsibility |
|---|---|
| `command.py` | The `@click.command()`. Owns **all** I/O: reads files, calls Moxfield, loads config — then hands plain dicts to logic and the result to render. |
| `logic.py` | Pure functions. No file access, no network, no printing. Takes and returns plain data. |
| `render.py` | Rich output only. Returns `None`. |
| `__init__.py` | Re-exports the click command. |

Commands are registered in `mtg_utils/main.py` via `cli.add_command()`. Tests mirror the split 1:1 at `tests/test_commands/test_<name>/test_{command,logic,render}.py` (with `__init__.py`).

`commands/compare_decks.py` is a single flat module that predates this pattern — don't use it as a template.

### The card pool

The domain model spans three commands; understanding it is the key to changing any of them.

```
Moxfield binder ──get_library()──►  card_library/owned_cards.txt      everything you own
                                              │
config.decks[*].file ◄─get_deck_list()─┐      │ configured decks consume copies
                                       └──────┤
                                              ▼
                                    card_library/available_cards.txt   owned − used by decks

card_library/purchased.txt ──Counter──► card_library/purchased_formatted.txt
  (one bare card name per copy,                    ("{qty} {name}")
   hand-edited)
```

- `update-card-library` is the **only** writer of the derived files. `check-missing-cards` and `show-shopping-list` read them and never write (except `show-shopping-list -o`).
- **`shared_decks`** (per-deck in `config.json`): the deck reuses copies already allocated to the listed sibling decks rather than consuming new ones from the library pool. `_incremental_shared_quantity()` in `update_card_library/logic.py` recurses through chained shares so overlapping chains aren't double-counted, and guards against cycles.
- **Purchased cards** count toward availability only for copies *not* already needed to cover a configured deck's deficit (see `deck_deficit` in `show_shopping_list/command.py`). A `*` in the output marks a card whose availability comes from the purchased file.

### Card line format

Every card file is one `{qty} {card name}` per line — except `purchased.txt`, which is bare names, repeated once per copy.

- `parse_card_list()` (`utils/cards.py`) **requires** the quantity prefix; it raises on a bare name.
- `parse_card_list_or_names()` tolerates both. Used for hand-written decklists passed to `show-shopping-list`.
- `library_sort_key()` (`utils/moxfield_api.py`) puts snow-covered basics last. Use it whenever writing `owned_cards.txt` / `available_cards.txt`.

### Shared utilities

- **Network** — all HTTP is confined to `utils/moxfield_api.py` (cloudscraper, because Moxfield sits behind Cloudflare). In tests, patch it where it is *imported*: `patch("mtg_utils.commands.<name>.command.get_deck_list")`.
- **Output** — always use `console` / `err_console` from `utils/console.py`, never bare `print`. Errors go to `err_console` followed by `raise SystemExit(1)`. Wrap card names, deck names and paths in `rich.markup.escape()`. Reusable table/panel builders (`card_table`, `panel_row`, `side_by_side`) live in `utils/panels.py`.
- **Config** — `utils/config.py` defines pydantic `AppConfig` / `DeckConfig`. Every config-aware command exposes `--config-file`, defaulting to `DEFAULT_CONFIG_FILE` (`compare-decks` takes no config).

### Tests

`tests/conftest.py` provides the `repo` fixture: it `chdir`s into `tmp_path` and returns a `make_config(...)` callable that writes a `config.json` and creates `card_library/decks/`. Use it for anything touching the filesystem. Mark tests `@pytest.mark.unit` (pure logic) or `@pytest.mark.integration` (CliRunner + filesystem + mocks).

## Gotchas

- `load_config()` **creates** `config.json` — with a hard-coded default binder id — when the file is absent. A mistyped `--config-file` silently writes a new file instead of failing.
- `card_library/available_cards.txt` and `card_library/owned_cards.txt` are hard-coded relative paths, **not** config-driven. Commands only work from the repo root; tests must `monkeypatch.chdir`.
- `config.json` and all of `card_library/` are committed to this repo, and `config.json` contains a real Moxfield binder id. (Older `.clinerules/` claimed both were gitignored — they are not.)
- Test layout is inconsistent: utils tests live in both `tests/*.py` and `tests/test_utils/`, and `list_decks` has tests in both `tests/test_list_decks.py` and `tests/test_commands/test_list_decks/`. Follow the `tests/test_commands/test_<name>/` layout for new work.
- `utils/decklists.py` (`render_decklist`, `render_multiple_decks`) is imported by nothing in `mtg_utils/` — only by `tests/test_utils/test_decklists.py`, which is what keeps it at 100% coverage. `list_decks/render.py` reimplements the same job. Reach for one or delete the other rather than adding a third.
- `[tool.coverage.report] exclude_also` in `pyproject.toml` excludes a literal source comment (`# Show cards that are in the deck but not needed`), so lines under it are invisible to coverage.
