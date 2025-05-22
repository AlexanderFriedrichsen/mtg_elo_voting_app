import os
import json
import random
import requests
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)

# Scryfall set code for Final Fantasy (as of June 2024)
NEWEST_SET_CODE = 'fin'  # Update if the set code changes
DATA_FILE = 'card_ratings.json'
ELO_K = 32

CARD_CACHE = []

# HTML template with tabs and JS for voting and animation
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CardRanker: Final Fantasy Set</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f0f0; }
        .container { max-width: 900px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px #ccc; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 30px; cursor: pointer; background: #eee; border-radius: 10px 10px 0 0; margin-right: 5px; }
        .tab.active { background: #fff; border-bottom: 2px solid #fff; font-weight: bold; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .cards { display: flex; justify-content: space-around; }
        .card { text-align: center; transition: opacity 1.2s; }
        .card.fade { opacity: 0.2; }
        img { max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px #aaa; }
        button { margin-top: 10px; padding: 10px 20px; font-size: 16px; border-radius: 5px; border: none; background: #0078d7; color: #fff; cursor: pointer; }
        button:hover { background: #005fa3; }
        .elo-change { font-size: 22px; font-weight: bold; color: #007800; margin-top: 8px; transition: none; position: relative; z-index: 2; }
        .elo-minus { color: #b00000; }
        .elo-change.sticky { position: absolute; left: 50%; transform: translateX(-50%); top: 10px; background: #fff; padding: 2px 8px; border-radius: 6px; box-shadow: 0 1px 4px #ccc; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 8px 12px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background: #f7f7f7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="tabs">
            <div class="tab active" id="vote-tab" onclick="showTab('vote')">Vote</div>
            <div class="tab" id="data-tab" onclick="showTab('data')">Data</div>
        </div>
        <div class="tab-content active" id="vote-content">
            <h1>Vote for the Better Card! (Final Fantasy Set)</h1>
            <form id="vote-form">
                <div class="cards">
                    {% for card in cards %}
                    <div class="card" id="card{{ loop.index }}" style="position:relative;">
                        <img src="{{ card['image_uris']['normal'] }}" alt="{{ card['name'] }}"><br>
                        <strong>{{ card['name'] }}</strong><br>
                        <button type="button" onclick="vote('{{ card['id'] }}')">Vote</button>
                        <input type="hidden" name="card{{ loop.index }}" value="{{ card['id'] }}">
                        <div class="elo-change sticky" id="elo{{ loop.index }}"></div>
                    </div>
                    {% endfor %}
                </div>
            </form>
            <p style="margin-top:30px; color:#888;">Card ratings are updated using Elo. Refresh to see new cards!</p>
        </div>
        <div class="tab-content" id="data-content">
            <h2>Current Elo Ratings</h2>
            <div id="elo-table"></div>
        </div>
    </div>
    <script>
    function showTab(tab) {
        document.getElementById('vote-tab').classList.remove('active');
        document.getElementById('data-tab').classList.remove('active');
        document.getElementById('vote-content').classList.remove('active');
        document.getElementById('data-content').classList.remove('active');
        document.getElementById(tab+'-tab').classList.add('active');
        document.getElementById(tab+'-content').classList.add('active');
        if(tab === 'data') loadEloTable();
    }
    function loadEloTable() {
        fetch('/data').then(r => r.json()).then(data => {
            let html = '<table><tr><th>Card Name</th><th>Elo</th></tr>';
            for(const row of data) {
                html += `<tr><td>${row.name}</td><td>${row.elo}</td></tr>`;
            }
            html += '</table>';
            document.getElementById('elo-table').innerHTML = html;
        });
    }
    function vote(winnerId) {
        let form = document.getElementById('vote-form');
        let card1 = form.card1.value;
        let card2 = form.card2.value;
        fetch('/vote', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({winner: winnerId, card1: card1, card2: card2})
        }).then(r => r.json()).then(data => {
            // Show Elo changes and fade out
            for(let i=1;i<=2;i++) {
                let el = document.getElementById('elo'+i);
                let cardDiv = document.getElementById('card'+i);
                let change = data['change'+i];
                let elo = data['elo'+i];
                let sign = change > 0 ? '+' : '';
                el.innerHTML = `Elo: ${elo} (<span class='${change>=0?'':'elo-minus'}'>${sign}${change}</span>)`;
                el.style.opacity = 1;
                el.style.display = 'block';
                cardDiv.classList.add('fade');
            }
            setTimeout(()=>{ window.location.reload(); }, 1700);
        });
    }
    </script>
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

@app.route('/data')
def data():
    cards = fetch_cards()
    ratings = load_ratings()
    # Build a list of dicts with name and elo, sorted by elo descending
    card_list = []
    for card in cards:
        elo = ratings.get(card['id'], 1200)
        card_list.append({'name': card['name'], 'elo': elo})
    card_list.sort(key=lambda x: x['elo'], reverse=True)
    return jsonify(card_list)

@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    winner_id = data['winner']
    card1_id = data['card1']
    card2_id = data['card2']
    ratings = load_ratings()
    r1 = ratings.get(card1_id, 1200)
    r2 = ratings.get(card2_id, 1200)
    if winner_id == card1_id:
        new_r1, new_r2 = get_elo(r1, r2, 1)
        change1 = round(new_r1 - r1, 2)
        change2 = round(new_r2 - r2, 2)
    else:
        new_r1, new_r2 = get_elo(r1, r2, 2)
        change1 = round(new_r1 - r1, 2)
        change2 = round(new_r2 - r2, 2)
    ratings[card1_id] = new_r1
    ratings[card2_id] = new_r2
    save_ratings(ratings)
    return jsonify({
        'elo1': new_r1, 'elo2': new_r2,
        'change1': change1, 'change2': change2
    })

if __name__ == '__main__':
    app.run(debug=True) 