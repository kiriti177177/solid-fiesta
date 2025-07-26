import json
import os

SESSION_FILE = "sessions.json"

def load_sessions():
    if not os.path.exists(SESSION_FILE):
        return {}
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_sessions(data):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_user_session(msg_id, session_data):
    data = load_sessions()
    data[str(msg_id)] = session_data
    save_sessions(data)

def get_session(msg_id):
    data = load_sessions()
    return data.get(str(msg_id))
