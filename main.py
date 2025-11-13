import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from flask_cors import CORS
from datetime import datetime

# Adjust these paths if your layout differs
BASE_DIR = os.path.dirname(__file__)               # backend/
TEMPLATES_DIR = os.path.join(BASE_DIR, '..', 'frontend')        # frontend/
STATIC_DIR = os.path.join(TEMPLATES_DIR, 'static')             # frontend/static
DATA_DIR = os.path.join(BASE_DIR, 'data')                     # backend/data

USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FINANCE_FILE = os.path.join(DATA_DIR, 'finance.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Create starter users.json and finance.json if missing (non-destructive)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        # example user: phone -> { name, password }
        json.dump({
            "9823533097": {"name": "Demo User", "password": "demo123"}
        }, f, indent=2)

if not os.path.exists(FINANCE_FILE):
    with open(FINANCE_FILE, 'w') as f:
        # example finance entry matching demo user above
        json.dump({
            "9823533097": {
                "bank_balance": 850000,
                "mutual_funds": 600000,
                "stocks": 400000,
                "loan": 300000,
                "credit_score": 820
            }
        }, f, indent=2)


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
CORS(app)


# ---------- Frontend pages ----------
@app.route('/')
def index():
    return render_template('login.html')


@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


@app.route('/chat_page', methods=['GET'])
def chat_page():
    return render_template('chat.html')


@app.route('/insights', methods=['GET'])
def insights_page():
        return render_template('insights.html')


@app.route('/portfolio', methods=['GET'])
def portfolio_page():
    return render_template('portfolio.html')


# Serve static files (if needed explicitly)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ---------- API endpoints ----------
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    phone = (data.get('phone') or '').strip()
    password = data.get('password') or ''

    if not phone or not password:
        return ("Missing phone or password", 400)

    users = load_json(USERS_FILE)
    user = users.get(phone)
    if not user or user.get('password') != password:
        return ("Invalid credentials", 401)

    # fetch finance for this user (may not exist)
    finance = load_json(FINANCE_FILE).get(phone, {})

    return jsonify({"success": True, "user": {"phone": phone, "name": user.get('name')}, "finance": finance})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    password = data.get('password') or ''

    if not name or not phone or not password:
        return ("Missing name/phone/password", 400)

    users = load_json(USERS_FILE)
    if phone in users:
        return (jsonify({"success": False, "message": "Phone already registered"}), 409)

    # ✅ Store all fields received from frontend instead of just name & password
    users[phone] = data

    save_json(USERS_FILE, users)

    # create a blank/default finance entry to be safe
    finances = load_json(FINANCE_FILE)
    finances.setdefault(phone, {
        "bank_balance": 0,
        "mutual_funds": 0,
        "stocks": 0,
        "loan": 0,
        "credit_score": 0
    })
    save_json(FINANCE_FILE, finances)

    return jsonify({"success": True, "message": "Registered successfully"})



@app.route('/mcp/<phone>', methods=['GET'])
def get_mcp(phone):
    phone = phone.strip()
    finances = load_json(FINANCE_FILE)
    entry = finances.get(phone)
    if entry is None:
        # return empty object rather than 404 for frontend convenience
        return jsonify({})
    return jsonify(entry)


@app.route('/update_finance/<phone>', methods=['POST'])
def update_finance(phone):
    """
    Optional helper to update finance data for a user.
    Expects JSON body containing fields to update (bank_balance, mutual_funds, stocks, loan, credit_score, etc.)
    """
    phone = phone.strip()
    updates = request.get_json(force=True, silent=True) or {}
    if not updates:
        return ("No data provided", 400)

    finances = load_json(FINANCE_FILE)
    entry = finances.get(phone, {})
    # merge updates (only keys present in updates)
    for k, v in updates.items():
        entry[k] = v
    finances[phone] = entry
    save_json(FINANCE_FILE, finances)
    return jsonify({"success": True, "finance": entry})


@app.route('/query', methods=['POST'])
def query():
    """
    Very simple chatbot / query endpoint.
    Accepts JSON { "phone": "...", "message": "..." }
    Returns a JSON reply using finance info when appropriate.
    """
    data = request.get_json(force=True, silent=True) or {}
    phone = (data.get('phone') or '').strip()
    message = (data.get('message') or '').lower()

    if not message:
        return jsonify({"reply": "I didn't get that. Please send a message."})

    finances = load_json(FINANCE_FILE)
    user_fin = finances.get(phone, {})

    # basic heuristics
    # ✅ Basic heuristics for financial queries
# You can place this inside your /chat or similar route

    # --- Bank Balance ---
    if any(word in message for word in ['balance', 'bank', 'savings']):
        bal = user_fin.get('bank_balance')
        if bal is None:
            return jsonify({"reply": "I don't have your bank balance information."})
        return jsonify({"reply": f"Your bank balance is ₹{bal:,}."})

    # --- Mutual Funds ---
    if any(word in message for word in ['mutual', 'mf', 'fund']):
        mf = user_fin.get('mutual_funds')
        if mf is None:
            return jsonify({"reply": "I don't have mutual funds information for you."})
        return jsonify({"reply": f"Your mutual funds are worth ₹{mf:,}."})

    # --- Stocks ---
    if any(word in message for word in ['stock', 'equity', 'shares']):
        s = user_fin.get('stocks')
        if s is None:
            return jsonify({"reply": "I don't have stock holdings information for you."})
        return jsonify({"reply": f"Your stock holdings are worth ₹{s:,}."})

    # --- Loan / Liabilities ---
    if any(word in message for word in ['loan', 'debt', 'liability', 'liabilities']):
        loan = user_fin.get('loan')
        if loan is None:
            return jsonify({"reply": "I don't have loan / liability details for you."})
        if loan == 0:
            return jsonify({"reply": "You have no active loans or liabilities."})
        return jsonify({"reply": f"Your current loan is ₹{loan:,}."})

    # --- Credit Score ---
    if any(word in message for word in ['credit', 'cibil', 'score']):
        cs = user_fin.get('credit_score')
        if cs is None:
            return jsonify({"reply": "Your credit score is not available."})
        return jsonify({"reply": f"Your credit score is {cs}."})

    # --- Total Net Worth ---
    if any(word in message for word in ['net worth', 'total worth', 'networth', 'worth']):
        bank = user_fin.get('bank_balance', 0)
        mf = user_fin.get('mutual_funds', 0)
        stocks = user_fin.get('stocks', 0)
        loan = user_fin.get('loan', 0)
        total_assets = bank + mf + stocks
        total_net_worth = total_assets - loan

        if total_net_worth < 0:
            return jsonify({"reply": f"Your liabilities exceed your assets by ₹{abs(total_net_worth):,}."})
        else:
            return jsonify({"reply": f"Your total net worth is ₹{total_net_worth:,}."})


    # fallback: simple echo + timestamp
    return jsonify({"reply": f"I am still Learning, I don't have information about it. \"{message}\" — (server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"})


# Simple heartbeat
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})


if __name__ == '__main__':
    # Run app on 0.0.0.0:5000 for local dev
    app.run(host='0.0.0.0', port=5000, debug=True)
