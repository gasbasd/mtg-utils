# mtg-utils – Copilot Instructions

Python CLI tool (Click + Poetry, Python ≥ 3.13) for managing Magic: The Gathering card collections and decks, backed by the Moxfield API.

## Build & Test

```sh
poetry install          # install dependencies
poetry run mtg-utils    # run the CLI
make test               # fast test run (no coverage) — for inner-loop dev
make coverage           # full test run with coverage enforcement + HTML report
make ci                 # lint + coverage — mirrors what GitHub Actions runs
make lint               # ruff check only
```

Tests pass on a clean checkout. Always run `make coverage` (or `poetry run pytest`) after changes to confirm 100% coverage is maintained. CI runs on every push/PR via `.github/workflows/ci.yml`.

## Architecture

```
mtg_utils/
  main.py                        # Click group; registers all commands
  commands/
    check_missing_cards.py       # check-missing-cards command
    compare_decks.py             # compare-decks command
    update_card_library.py       # update-library command
  utils/
    config.py                    # load_config(), DEFAULT_CONFIG_FILE
    readers.py                   # read_list() – strips blank lines
    moxfield_api.py              # get_deck_list(), get_library() via cloudscraper
```

All external HTTP goes through `moxfield_api.py`. Mock it in tests with `unittest.mock.patch`.

## Key Conventions

- **Card format** (everywhere): `{quantity} {card name}` per line, e.g. `2 Lightning Bolt`.
- **Config** (`config.json`): defines `binder_id`, `purchased_file`, and `decks` map with `id` and `file` per deck. Optional `shared_decks` list per deck re-uses cards from sibling decks without double-counting from the library pool.
- **Data files** live under `card_library/` and `decklists/`; sorting order is preserved by `library_sort_key` (snow lands last, then alphabetical).
- **CWD matters**: commands resolve paths relative to the process CWD. Tests use `monkeypatch.chdir(tmp_path)` to isolate file I/O.

## Testing Patterns

- Use `click.testing.CliRunner` for end-to-end CLI tests.
- Use `tmp_path` for all file I/O; never write to real `card_library/` in tests.
- Use the `repo` fixture from `tests/conftest.py` (chdir + `make_config` helper) for new CLI/filesystem tests.
- Test files follow `tests/test_<module>.py` naming.
- Mock network calls: `patch("mtg_utils.commands.<cmd>.get_deck_list", ...)`.
- Mark tests: `@pytest.mark.unit` (pure logic) or `@pytest.mark.integration` (CLI + filesystem). Run a subset with `pytest -m unit` or `pytest -m integration`.

## Agents & Skills

| Name | Purpose |
|---|---|
| [MTG Library Maintainer](.github/agents/mtg-library-maintainer.agent.md) | Collection data, deck files, config, command implementation |
| [MTG QA](.github/agents/mtg-qa.agent.md) | Write and run pytest tests only |
| [MTG Orchestrator](.github/agents/mtg-orchestrator.agent.md) | End-to-end tasks spanning both implementation and tests |
| [CI Engineer](.github/agents/ci-engineer.agent.md) | GitHub Actions workflows, Makefile CI targets |

For feature work or bug fixes that need tests, prefer the **MTG Orchestrator** agent.
