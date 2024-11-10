from flask import Flask, request, render_template_string
import os
import json
from x_ray_feature import run_xray_with_json
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

# Database and Superset settings
DB_CONNECTION_STRING = 'mysql+pymysql://superset_user3:dhatchan@localhost/superset_dbb'
TABLE_NAME = 'rester_sample'
DATASET_NAME = 'rester_sample'
DASHBOARD_TITLE = 'Auto-generated Dashboard'
DATABASE_ID = 1
SCHEMA = 'superset_dbb'

SUPERSET_BASE_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
GUEST_TOKEN_ENDPOINT = f"{SUPERSET_BASE_URL}/api/v1/security/guest_token/"

def find_json_file(user_query):
    user_query = user_query.lower()
    for keyword, file_path in data_files.items():
        if keyword in user_query:
            return file_path
    return None

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

def generate_guest_token(dashboard_id):
    headers = authenticate()
    guest_token_payload = {
        "resources": [{"type": "dashboard", "id": dashboard_id}],
        "user": {"username": "embed_user"},
        "rls": []
    }
    response = requests.post(GUEST_TOKEN_ENDPOINT, headers=headers, json=guest_token_payload)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception(f"Failed to generate guest token {response.json()}")

@app.route('/', methods=['GET', 'POST'])
def index():
    response_message = ""
    embed_url = ""
    
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        json_file = find_json_file(query)

        if json_file and os.path.exists(json_file):
            # Load the JSON file and pass it to the xray script
            with open(json_file, 'r') as file:
                json_file = json.load(file)
            try:
                # Run x-ray feature to load data and create the dashboard
                embed_url = run_xray_with_json(
                    file_path=json_file,
                    db_connection_string=DB_CONNECTION_STRING,
                    table_name=TABLE_NAME,
                    dataset_name=DATASET_NAME,
                    dashboard_title=DASHBOARD_TITLE,
                    database_id=DATABASE_ID,
                    schema=SCHEMA
                )
                
                response_message = f"Dashboard created and embedded successfully for '{query}'."
            except Exception as e:
                response_message = f"Error creating dashboard: {str(e)}"
        else:
            response_message = "No matching data file found for your query."

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Data Loader</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f4f4f4;
                }
                .container {
                    text-align: center;
                    background: #ffffff;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    width: 90%;
                }
                h1 {
                    font-size: 1.8em;
                    margin-bottom: 0.5em;
                }
                input[type="text"] {
                    width: 100%;
                    padding: 8px;
                    margin: 8px 0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                button {
                    width: 48%;
                    padding: 10px;
                    margin: 5px 1%;
                    font-size: 1em;
                    color: #fff;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button[type="submit"] {
                    background-color: #007BFF;
                }
                button[type="button"] {
                    background-color: #28A745;
                }
                button:hover {
                    opacity: 0.9;
                }
                .response-message {
                    color: #555;
                    margin-top: 1em;
                }
                .embed-container {
                    margin-top: 20px;
                }
                #loading-overlay {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.6);
                    color: #fff;
                    font-size: 1.5em;
                    font-weight: bold;
                    text-align: center;
                    padding-top: 30%;
                    z-index: 1000;
                }
            </style>
            <script>
                function startDictation() {
                    if (window.hasOwnProperty('webkitSpeechRecognition')) {
                        var recognition = new webkitSpeechRecognition();
                        recognition.continuous = false;
                        recognition.interimResults = false;
                        recognition.lang = "en-US";
                        recognition.start();

                        recognition.onresult = function(event) {
                            document.getElementById('query').value = event.results[0][0].transcript;
                            recognition.stop();
                        };

                        recognition.onerror = function() {
                            recognition.stop();
                        }
                    }
                }
                
                function showLoading() {
                    document.getElementById('loading-overlay').style.display = 'block';
                }
            </script>
        </head>
        <body>
            <div id="loading-overlay">Creating dashboard and charts. Please wait...</div>
            <div class="container">
                <h1>Data Loader</h1>
                <form method="post" onsubmit="showLoading()">
                    <input type="text" id="query" name="query" placeholder="Enter data type..." required>
                    <button type="submit">Load Data</button>
                    <button type="button" onclick="startDictation()">🎙️ Speak</button>
                </form>
                <p class="response-message">{{ response_message }}</p>
                
                {% if embed_url %}
                <div class="embed-container">
                    <h2>Embedded Dashboard</h2>
                    <iframe src="{{ embed_url }}&standalone=1" width="100%" height="800px" frameborder="0" style="border:0;"></iframe>
                </div>
                {% endif %}
            </div>
        </body>
        </html>
    ''', response_message=response_message, embed_url=embed_url)

if __name__ == '__main__':
    app.run(debug=True)
