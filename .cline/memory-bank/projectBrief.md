# Project Brief

## Objective

mtg-utils is a command-line utility designed for managing Magic: The Gathering card collections, decks, and performing various analyses. It helps users track their card collections from Moxfield, manage multiple decks, check missing cards, and monitor newly purchased cards.

---

## Technology Stack

| Component | Technology |
|-----------|-------------|
| Python Version | >=3.13 |
| Package Manager | Poetry |
| CLI Framework | Click |
| HTTP Requests | Requests + Cloudscraper |
| Data Validation | Pydantic |
| Console Output | Rich |
| Testing | pytest + pytest-cov |
| Linting | Ruff + Pyright |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mtg-utils update-library` | Update card collection and decks from Moxfield |
| `mtg-utils check-missing-cards` | Check missing cards for a deck |
| `mtg-utils compare-decks` | Compare two decks for card differences |
| `mtg-utils list-decks` | List configured decks with card contents |

---

## list-decks Command Details

The `list-decks` command displays all configured decks with their actual card contents:

```
─────── Configured decks with card contents ───────
─────── gretchen (100 cards) ───────
1 Aether Spellbomb
1 Arbor Elf
...
```

**Features:**

- Shows deck alias with card count
- Displays all cards sorted alphabetically
- Empty line separation between decks
- Modular architecture with reusable rendering logic

**Usage:**

```bash
mtg-utils list-decks [--config-file PATH]
