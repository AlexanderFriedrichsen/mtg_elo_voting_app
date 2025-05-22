# CardRanker: Final Fantasy Set

A simple Flask web app to vote on Magic: The Gathering cards from the newest set (Final Fantasy, set code: `ffxvi`) using the Scryfall API. Card ratings are updated using the Elo system and stored locally.

## Setup

1. **Clone the repo and create a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the app:**
   ```powershell
   python app.py
   ```
4. **Open your browser:**
   Go to [http://127.0.0.1:5000](http://127.0.0.1:5000)

## How it works
- Two random cards from the Final Fantasy set are shown.
- Click "Vote" on the card you think is better.
- The app updates the Elo ratings for both cards in `card_ratings.json`.
- Refresh to see new pairs and keep voting!

## Notes
- The set code for Final Fantasy is set to `ffxvi` (update in `app.py` if needed).
- All data is local; no accounts or logins required.
- To reset ratings, delete `card_ratings.json`. 