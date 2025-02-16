from flask import Flask, request, jsonify
import openai
import sqlite3
from datetime import datetime

app = Flask(__name__)
openai.api_key = "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"  # Replace with your OpenAI API key

# Database setup for user authentication and progress tracking
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (user_id INTEGER, topic TEXT, progress FLOAT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

# Function to register a new user
def register_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

# Function to authenticate a user
def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user_id = c.fetchone()
    conn.close()
    return user_id[0] if user_id else None

# Function to track user progress
def track_progress(user_id, topic, progress):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO progress (user_id, topic, progress, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, topic, progress, datetime.now()))
    conn.commit()
    conn.close()

# Function to generate a concept map with explanations for connections
def generate_concept_map_with_explanations(topic):
    prompt = f"Generate a list of key concepts related to {topic}, along with their relationships and explanations for how they are connected. Format: Concept -> Related Concept: Explanation"
    response = openai.ChatCompletion.create(
        model="gpt-4", 
        messages=[{"role": "system", "content": "You are a concept mapping assistant."},
                  {"role": "user", "content": prompt}]
    )
    concepts = response["choices"][0]["message"]["content"].split("\n")
    concept_map = []
    for concept in concepts:
        if "->" in concept:
            parts = concept.split(": ")
            if len(parts) == 2:
                relationship, explanation = parts
                concept1, concept2 = relationship.split(" -> ")
                concept_map.append((concept1, concept2, explanation))
    return concept_map

# Flask API endpoint to generate and return a concept map
@app.route('/generate_map', methods=['POST'])
def generate_map():
    data = request.json
    topic = data.get("topic")
    if not topic:
        return jsonify({"error": "Please provide a topic"}), 400
    concepts = generate_concept_map_with_explanations(topic)
    return jsonify({"concept_map": concepts})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)  # Run Flask on port 5000