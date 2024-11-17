from flask import Flask, request, render_template_string, jsonify
import os
import json
import sqlite3
import requests

app = Flask(__name__)

# Mapping user input keywords to JSON file paths
data_files = {
    "code review": "D:/CodeKata/chat-ui/datasets/code_review.json",
    "project management": "D:/CodeKata/chat-ui/datasets/project_management.json",
    "feedback": "D:/CodeKata/chat-ui/datasets/feedback.json",
    "sales": "D:/CodeKata/chat-ui/datasets/sales_data.json",
    "inventory": "D:/CodeKata/chat-ui/datasets/inventory.json",
}

# Database setup
DATABASE = 'dashboard_app.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Search history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Config table
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Superset settings
SUPERSET_BASE_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"

def authenticate():
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "provider": "db",
        "refresh": True
    }
    response = requests.post(f"{SUPERSET_BASE_URL}/api/v1/security/login", json=login_data)
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        csrf_response = requests.get(f"{SUPERSET_BASE_URL}/api/v1/security/csrf_token/", headers=headers)
        if csrf_response.status_code == 200:
            csrf_token = csrf_response.json().get("result")
            headers["X-CSRFToken"] = csrf_token
            headers["Content-Type"] = "application/json"
            return headers
    raise Exception("Authentication failed")

# =========================
# Search History Endpoints
# =========================

@app.route('/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT query, timestamp FROM history ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    history = [{"query": row["query"], "timestamp": row["timestamp"]} for row in rows]
    return jsonify({"history": history})

@app.route('/history', methods=['POST'])
def add_to_history():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO history (query) VALUES (?)', (query,))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Query added successfully"})

@app.route('/history', methods=['DELETE'])
def clear_history():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM history')
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "History cleared successfully"})

# =========================
# Config Endpoints
# =========================

@app.route('/config', methods=['POST'])
def save_config():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key or not value:
        return jsonify({"error": "Key and value are required"}), 400
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO config (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Configuration saved successfully"})

@app.route('/config', methods=['GET'])
def get_config():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM config')
    rows = c.fetchall()
    conn.close()
    config = [{"key": row["key"], "value": row["value"]} for row in rows]
    return jsonify({"config": config})

# =========================
# Existing Functionality - JSON to Dashboard
# =========================

def find_json_file(user_query):
    user_query = user_query.lower()
    for keyword, file_path in data_files.items():
        if keyword in user_query:
            return file_path
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    response_message = ""
    embed_url = ""
    
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        json_file = find_json_file(query)

        if json_file and os.path.exists(json_file):
            # Save the query to history
            add_to_history({"query": query})

            # Load the JSON file and process it
            with open(json_file, 'r') as file:
                json_file = json.load(file)
            try:
                embed_url = run_xray_with_json(
                    file_path=json_file,
                    db_connection_string='mysql+pymysql://superset_user3:dhatchan@localhost/superset_dbb',
                    table_name='rester_sample',
                    dataset_name='rester_sample',
                    dashboard_title='Auto-generated Dashboard',
                    database_id=1,
                    schema='superset_dbb'
                )
                response_message = f"Dashboard created successfully for '{query}'."
            except Exception as e:
                response_message = f"Error creating dashboard: {str(e)}"
        else:
            response_message = "No matching data file found for your query."

    return render_template_string('''<!DOCTYPE html>...</html>''', response_message=response_message, embed_url=embed_url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
