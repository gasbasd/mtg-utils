---
name: run-command
description: 'Maintain MTG collection and deck data in this repo. Use for updating the card library from Moxfield, recording purchased cards, checking missing cards for a deck, comparing deck files, adjusting config-driven deck sharing, or editing card_library and decklists data while preserving existing CLI workflows and text formats.'
argument-hint: 'Describe the deck, card-library, config, or command workflow to update'
user-invocable: true
---

# Run Command

## What This Skill Does

Use this skill for repeatable MTG collection and deck maintenance tasks in this repository. It keeps changes aligned with the existing Python CLI, the `config.json` deck configuration, and the plain-text card files under `card_library/` and `decklists/`.

Prefer this skill when the task is about:
- updating owned, purchased, or available card data
- syncing configured decks from Moxfield
- checking which cards are missing for a deck
- comparing two deck files
- editing deck or collection text files without breaking the current formats

Do not use this skill for unrelated Python refactors, repo-wide cleanup, or inventing new workflows when the existing commands already cover the task.

## Repository Workflow

### 1. Inspect Before Changing

Start by reading the files that define the current workflow:
- `config.json` for binder, deck file paths, deck ids, and optional `shared_decks`
- `mtg_utils/main.py` for available CLI entry points
- `mtg_utils/commands/update_card_library.py` for library, purchased-card, and shared-deck behavior
- `mtg_utils/commands/check_missing_cards.py` for missing-card reporting
- `mtg_utils/commands/compare_decks.py` for deck comparison output
- relevant files in `card_library/` or `decklists/`

If the task touches data only, confirm whether the requested change should be made by editing text files directly or by running the existing CLI to regenerate derived files.

### 2. Choose the Right Path

Pick the workflow that matches the request.

#### Update collection state

Use the update-library flow when the user wants to:
- refresh owned cards from the configured binder
- sync configured decks from Moxfield
- rebuild `card_library/available_cards.txt`
- process `card_library/purchased.txt` into `card_library/purchased_formatted.txt`

Relevant command:

```sh
mtg-utils update-library
```

Decision points:
- If `config.json` is missing or wrong, fix config first.
- If `purchased_file` does not exist, expect the workflow to create an empty file.
- If a deck declares `shared_decks`, treat matching cards in those decks as reusable before consuming copies from the library pool.

#### Check missing cards

Use the missing-card flow when the user wants to evaluate one target deck against the current available pool.

Relevant commands:

```sh
mtg-utils check-missing-cards --deck-file path/to/deck.txt
mtg-utils check-missing-cards --moxfield-id your-deck-id
```

Decision points:
- Use `--deck-file` for local text decks.
- Use `--moxfield-id` for one-off remote deck checks.
- Never pass both options together.

The output should distinguish:
- cards already available
- cards completely missing
- cards available in other configured decks

#### Compare decks

Use the comparison flow to understand overlap or divergence between two local deck files.

Relevant command:

```sh
mtg-utils compare-decks --deck1-file path/to/deck1.txt --deck2-file path/to/deck2.txt
```

This should report:
- cards in common
- cards unique to the first deck
- cards unique to the second deck

#### Edit config or text data

Use direct file edits when the task is to:
- change deck ids or file paths in `config.json`
- add or adjust `shared_decks`
- edit `card_library/purchased.txt`
- fix or curate deck text files

When editing plain-text card files:
- preserve the existing one-entry-per-line style
- preserve `quantity card name` formatting where the file already uses it
- avoid changing sort order unless the task explicitly requires it or a command regenerates the file

### 3. Validate the Result

After changes, validate with the lightest check that proves the requested outcome.

Preferred validation:
- run the relevant CLI command when the task changes command behavior or derived files
- inspect the updated card or deck files when the task is data-only
- confirm that missing-card or compare output still matches the expected structure

Check for these completion criteria:
- `config.json` remains valid JSON
- deck file paths in config point to the expected files
- generated card files exist where the command expects them
- `shared_decks` references only configured deck names
- collection math is consistent with owned cards, purchased cards, and consumed deck cards
- no unrelated refactors or format churn were introduced

## Output Expectations

When using this skill, return a concise result that states:
- what changed
- which files or commands were used
- any effect on available, owned, purchased, or deck data
- any ambiguity, warning, or follow-up needed

## Example Requests

- `/mtg-library-maintainer update purchased cards and rebuild available_cards.txt`
- `/mtg-library-maintainer check what I am missing for decklists/gretchen_pdc2.txt`
- `/mtg-library-maintainer compare card_library/decks/gretchen.txt with card_library/decks/tatyova.txt`
- `/mtg-library-maintainer add deck sharing from gretchen to weavers in config.json and verify availability math`
