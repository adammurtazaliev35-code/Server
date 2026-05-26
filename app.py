from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import datetime
import jwt
from functools import wraps

app = Flask(__name__)
CORS(app)

# Секретный ключ для подписи токенов (в продакшене выносится в .env)
app.config['SECRET_KEY'] = 'super-secret-key-for-vkr-2026'

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

# --- ДЕКОРАТОР БЕЗОПАСНОСТИ (JWT) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Ищем токен в заголовках
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Токен отсутствует, доступ запрещен"}), 401
        
        try:
            # Расшифровываем токен
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Срок действия токена истек. Войдите заново"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Недействительный токен"}), 401
            
        # Если всё отлично, передаем ID пользователя в функцию
        return f(current_user_id, *args, **kwargs)
    return decorated


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
        # ВМЕСТО ID ВЫДАЕМ ТОКЕН (действует 24 часа)
        token = jwt.encode({
            'user_id': user[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({"success": True, "token": token, "username": username})
    
    return jsonify({"error": "Неверный логин или пароль"}), 401


# --- ЭНДПОИНТЫ ДЛЯ ДАННЫХ (ВКР: Хранение) ---

@app.route('/api/save_prompt', methods=['POST'])
@token_required
def save_prompt(current_user_id):
    # ID пользователя теперь берется из токена (current_user_id), а не из JSON от фронтенда
    data = request.json
    p_type = data.get('type')
    inp = data.get('input')
    out = data.get('output')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO saved_prompts (user_id, prompt_type, input_text, output_text) VALUES (?, ?, ?, ?)",
                       (current_user_id, p_type, inp, out))
        conn.commit()
    return jsonify({"success": True})

# УБРАЛИ <int:user_id> из пути. Сервер сам знает, кто делает запрос.
@app.route('/api/get_last_prompts', methods=['GET'])
@token_required
def get_last_prompts(current_user_id):
    result = {"positive": None, "negative": None}
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Получаем последний положительный промпт для авторизованного пользователя
        cursor.execute("""
            SELECT input_text, output_text FROM saved_prompts 
            WHERE user_id = ? AND prompt_type = 'positive' 
            ORDER BY created_at DESC LIMIT 1
        """, (current_user_id,))
        pos = cursor.fetchone()
        if pos:
            result["positive"] = {"input": pos[0], "output": pos[1]}
            
        # Получаем последний отрицательный промпт
        cursor.execute("""
            SELECT input_text, output_text FROM saved_prompts 
            WHERE user_id = ? AND prompt_type = 'negative' 
            ORDER BY created_at DESC LIMIT 1
        """, (current_user_id,))
        neg = cursor.fetchone()
        if neg:
            result["negative"] = {"input": neg[0], "output": neg[1]}
            
    return jsonify(result)

# УБРАЛИ <int:user_id> из пути
@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT prompt_type, input_text, output_text, created_at FROM saved_prompts WHERE user_id = ? ORDER BY created_at DESC", (current_user_id,))
        history = cursor.fetchall()
    return jsonify(history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
