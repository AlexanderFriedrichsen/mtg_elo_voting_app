import os
import json
import random
import requests
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Scryfall set code for Final Fantasy (as of June 2024)
NEWEST_SET_CODE = 'ffxvi'  # Update if the set code changes
DATA_FILE = 'card_ratings.json'
ELO_K = 32

CARD_CACHE = []

# HTML template
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CardRanker: Final Fantasy Set</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f0f0; }
        .container { max-width: 800px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px #ccc; }
        .cards { display: flex; justify-content: space-around; }
        .card { text-align: center; }
        img { max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px #aaa; }
        button { margin-top: 10px; padding: 10px 20px; font-size: 16px; border-radius: 5px; border: none; background: #0078d7; color: #fff; cursor: pointer; }
        button:hover { background: #005fa3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Vote for the Better Card! (Final Fantasy Set)</h1>
        <form method="post" action="/vote">
            <div class="cards">
                {% for card in cards %}
                <div class="card">
                    <img src="{{ card['image_uris']['normal'] }}" alt="{{ card['name'] }}"><br>
                    <strong>{{ card['name'] }}</strong><br>
                    <button name="winner" value="{{ card['id'] }}">Vote</button>
                    <input type="hidden" name="card{{ loop.index }}" value="{{ card['id'] }}">
                </div>
                {% endfor %}
            </div>
        </form>
        <p style="margin-top:30px; color:#888;">Card ratings are updated using Elo. Refresh to see new cards!</p>
    </div>
</body>
</html>
'''

def fetch_cards():
    """Fetch all cards from the newest set and cache them."""
    global CARD_CACHE
    if CARD_CACHE:
        return CARD_CACHE
    url = f'https://api.scryfall.com/cards/search?order=set&q=e%3A{NEWEST_SET_CODE}&unique=prints'
    cards = []
    while url:
        resp = requests.get(url)
        data = resp.json()
        cards.extend([c for c in data['data'] if 'image_uris' in c])
        url = data.get('next_page')
    CARD_CACHE = cards
    return cards

def load_ratings():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_ratings(ratings):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(ratings, f, indent=2)

def get_elo(r1, r2, winner):
    """Update Elo ratings for two players."""
    expected1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
    expected2 = 1 / (1 + 10 ** ((r1 - r2) / 400))
    if winner == 1:
        r1 += ELO_K * (1 - expected1)
        r2 += ELO_K * (0 - expected2)
    else:
        r1 += ELO_K * (0 - expected1)
        r2 += ELO_K * (1 - expected2)
    return round(r1, 2), round(r2, 2)

@app.route('/', methods=['GET'])
def index():
    cards = fetch_cards()
    card1, card2 = random.sample(cards, 2)
    return render_template_string(TEMPLATE, cards=[card1, card2])

@app.route('/vote', methods=['POST'])
def vote():
    winner_id = request.form['winner']
    card1_id = request.form['card1']
    card2_id = request.form['card2']
    ratings = load_ratings()
    # Default Elo rating
    r1 = ratings.get(card1_id, 1200)
    r2 = ratings.get(card2_id, 1200)
    if winner_id == card1_id:
        new_r1, new_r2 = get_elo(r1, r2, 1)
    else:
        new_r1, new_r2 = get_elo(r1, r2, 2)
    ratings[card1_id] = new_r1
    ratings[card2_id] = new_r2
    save_ratings(ratings)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 