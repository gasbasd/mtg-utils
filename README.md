# MTG-Utils

A command-line utility for managing Magic: The Gathering card collections, decks, and performing various analyses.

## Features

- Track your card collection from Moxfield
- Manage multiple decks
- Check which cards you're missing for a deck
- Find cards in your collection that are used in multiple decks
- Keep track of newly purchased cards

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
mtg-utils update-library
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
