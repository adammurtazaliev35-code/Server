from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# Инициализация базы данных
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        # Таблица сохраненных промптов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt_type TEXT, -- 'positive' или 'negative'
                input_text TEXT,
                output_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

init_db()

# --- ЭНДПОИНТЫ БЕЗОПАСНОСТИ ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Заполните все поля"}), 400
    
    # Хеширование пароля (защита от компрометации БД)
    hashed_password = generate_password_hash(password)
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                           (username, hashed_password))
            conn.commit()
        return jsonify({"success": True, "message": "Регистрация успешна"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Пользователь уже существует"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
    if user and check_password_hash(user[1], password):
        return jsonify({"success": True, "userId": user[0], "username": username})
    
    return jsonify({"error": "Неверный логин или пароль"}), 401

# --- ЭНДПОИНТЫ ДЛЯ ДАННЫХ (ВКР: Хранение) ---

@app.route('/api/save_prompt', methods=['POST'])
def save_prompt():
    data = request.json
    user_id = data.get('userId')
    p_type = data.get('type')
    inp = data.get('input')
    out = data.get('output')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO saved_prompts (user_id, prompt_type, input_text, output_text) VALUES (?, ?, ?, ?)",
                       (user_id, p_type, inp, out))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT prompt_type, input_text, output_text, created_at FROM saved_prompts WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        history = cursor.fetchall()
    return jsonify(history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
