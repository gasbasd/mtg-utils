# Product Context

## Why This Project Exists

mtg-utils addresses the challenges Magic: The Gathering players face when managing complex card collections and multiple decklists. The tool was created to:

1. **Track Collection Progress** - Easily see which cards are missing from your collection by comparing against decklists
2. **Manage Multiple Decks** - Handle several deck configurations without manual tracking
3. **Monitor Purchases** - Keep track of newly purchased cards and their status
4. **Compare Decks** - Quickly identify differences between deck variations

## Problems It Solves

### Manual Collection Tracking

MTG players often struggle with tracking cards across multiple decks and collections. mtg-utils automates this by:

- Syncing with Moxfield to get your complete collection
- Maintaining an `available_cards.txt` file that accounts for owned, purchased, and used cards
- Providing clear missing card reports for any deck

### Deck Comparison

Comparing decklists manually is error-prone. The `compare-decks` command:

- Shows cards in one deck but not the other
- Highlights count differences for shared cards
- Provides side-by-side comparison reports

### Collection Updates

Keeping track of new purchases and updates requires manual work. mtg-utils:

- Automatically updates your collection from Moxfield
- Tracks purchased cards separately
- Updates available card counts

## User Experience Goals

1. **CLI-First** - Fast, efficient workflow for users comfortable with command line
2. **Clear Output** - Formatted tables and panels using Rich library
3. **Modular Design** - Easy to add new commands and extend functionality
4. **Consistent Documentation** - All features documented following project standards

---

## Core Features

| Feature | Description |
|---------|-------------|
| `update-library` | Sync collection and decks from Moxfield |
| `check-missing-cards` | Find cards needed for a deck |
| `compare-decks` | Compare two decklists for differences |
| `list-decks` | Show all configured decks with card contents |

## list-decks Command

The `list-decks` command displays all configured decks with their card contents:

```
─────── Configured decks with card contents ───────
─────── gretchen (100 cards) ───────
1 Aether Spellbomb
1 Arbor Elf
1 Arcane Denial
...

─────── lagrella (100 cards) ───────
1 Arcane Denial
1 Arcane Signet
...
```

**Features:**

- Shows deck alias with card count
- Displays all cards sorted alphabetically
- Empty line separation between decks
- Modular architecture with reusable rendering logic
