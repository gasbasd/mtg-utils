# MTG-Utils

A command-line utility for managing Magic: The Gathering card collections, decks, and performing various analyses.

## Features

- Track your card collection from Moxfield
- Manage multiple decks
- Check which cards you're missing for a deck
- Generate a consolidated shopping list across multiple planned decks
- Find cards in your collection that are used in multiple decks
- Keep track of newly purchased cards
- Turn a CardTrader order export into a Moxfield collection import

## Installation

### Option 1: Using Poetry (recommended)

1. Make sure you have Poetry installed. If not, install it:

   ```sh
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Clone the repository:

   ```sh
   git clone https://github.com/yourusername/mtg-utils.git
   cd mtg-utils
   ```

3. Install dependencies with Poetry:

   ```sh
   poetry install
   ```

4. Activate the Poetry shell:

   ```sh
   poetry shell
   ```

### Option 2: Using virtualenv

1. Clone the repository:

   ```sh
   git clone https://github.com/yourusername/mtg-utils.git
   cd mtg-utils
   ```

2. Create a virtual environment:

   ```sh
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On macOS/Linux:

     ```sh
     source venv/bin/activate
     ```

   - On Windows:

     ```sh
     venv\Scripts\activate
     ```

4. Install the package in development mode:

   ```sh
   pip install -e .
   ```

## Configuration

Create a configuration file at config.json or run the update library command to
create example file:

```json
{
  "binder_id": "your-moxfield-binder-id",
  "decks": {
    "deck1": {
      "file": "card_library/decks/deck1.txt",
      "id": "moxfield-deck-id-1"
    },
    "deck2": {
      "file": "card_library/decks/deck2.txt",
      "id": "moxfield-deck-id-2"
    }
  },
  "purchased_file": "card_library/purchased.txt"
}
```

## Usage

### Update Card Library

Update your card collection and decks from Moxfield:

```sh
mtg-utils update-card-library
```

#### Record purchased cards

Add purchased cards to purchased.txt (one card name per line, repeated for multiple copies) and this command will add the purchased cards to your available collection (`available_cards.txt`).

### Check Missing Cards

Check which cards are missing for a specific deck:

```sh
mtg-utils check-missing-cards --deck-file path/to/decklist.txt
```

Or check against a Moxfield deck:

```sh
mtg-utils check-missing-cards --moxfield-id your-moxfield-deck-id
```

### Show Shopping List

Generate a consolidated shopping list across multiple planned decks. Cards you need to buy are shown with the decks that requested them and which configured decks already use the card. Cards you already have are shown in a separate panel, with `*` marking cards sourced from your purchased file.

```sh
# Two local deck files
mtg-utils show-shopping-list -d decklists/deck_a.txt -d decklists/deck_b.txt

# Mix of local file and Moxfield deck
mtg-utils show-shopping-list -d decklists/deck_a.txt -id your-moxfield-deck-id

# Save the buy list to a file
mtg-utils show-shopping-list -d decklists/deck_a.txt -o decklists/to_buy.txt
```

Options:

- `-d / --deck-file` — path to a deck file (repeatable)
- `-id / --moxfield-id` — Moxfield deck ID (repeatable)
- `-o / --output-file` — write the buy list to a file in `{qty} {card name}` format (optional)

> **Note:** Purchased cards (`purchased_formatted.txt`) only count toward your available pool for copies not already needed to fill a configured library deck.

### Convert CardTrader Order

Turn the `.xls` export of a CardTrader order into a CSV you can feed straight to Moxfield's
collection importer:

```sh
# Writes cardtrader_order_20260901rvin7i-moxfield.csv next to the input
mtg-utils convert-cardtrader-order cardtrader_order_20260901rvin7i.xls

# Choose the destination yourself
mtg-utils convert-cardtrader-order order.xls -o ready-to-import.csv
```

Options:

- `ORDER_FILE` — the `.xls` CardTrader emailed you (positional, required)
- `-o / --output-file` — where to write the CSV (default: `<order file>-moxfield.csv`)

The conversion renames CardTrader's columns to Moxfield's, strips the zero padding from
collector numbers, converts prices from cents to euros, turns the foil flag into `foil`, and
maps card conditions (`Slightly Played` becomes `Lightly Played`) and language codes (`jp`
becomes `ja`). Rows for other games are dropped and listed in the summary; an unrecognised
condition aborts the run rather than importing something wrong.

CardTrader also invents set codes and decorates card names, which Moxfield then rejects. Every
row is therefore checked against Scryfall before the CSV is written — by set and collector
number first, retried as a token, then by name — and the confirmed printing is what gets
written. Everything that changed is listed in a **Corrected** panel:

```
╭───────────────────────────── Corrected: 10 ──────────────────────────────╮
│ Goblin Army // Human Soldier | HOB T 4/2  → Goblin Army | THOB 4         │
│ Guidelight Pathmaker (Borderless) | CDFT 324 → Guidelight Pathmaker | DFT 324 │
│ Spirit Link (Retro Frame) | CDMR 274      → Spirit Link | DMR 274        │
╰──────────────────────────────────────────────────────────────────────────╯
```

Rows Scryfall cannot confirm are written unchanged and listed under **Not found on Scryfall**
so you can fix them by hand — typically CardTrader pseudo-sets like `PWPN` that lump years of
promos together. Check the Corrected panel too: where CardTrader's own numbering is ambiguous
the match is a best effort, not a guarantee.

Requests are throttled to stay inside Scryfall's rate limit, and a rate-limited or failing
request is retried with an escalating backoff, announced on stderr as it waits. If Scryfall
stays unreachable the command still writes the CSV, keeps every printing it had already
confirmed, and says which ones went unverified.

## Directory Structure

After running the commands, you'll have a directory structure like:

```sh
card_library/
  owned_cards.txt # your moxfield library
  available_cards.txt # your moxfiled library + purchased cards - used cards
  purchased.txt # your purchased file
  purchased_formatted.txt # purchased file with quantities
  decks/ # deck lists provided in config.json
    deck1.txt
    deck2.txt
    ...
```
