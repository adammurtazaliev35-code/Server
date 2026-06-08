from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import jwt
from functools import wraps
import os

from database import init_db, get_db_connection
from prompt_builder import build_prompt

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-for-vkr-2026')

# Инициализируем БД (создаёт таблицы и наполняет словарь)
init_db()

# --- ДЕКОРАТОР JWT (без изменений) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        if not token:
            return jsonify({"error": "Токен отсутствует"}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Токен истёк"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Недействительный токен"}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# --- ЭНДПОИНТЫ АВТОРИЗАЦИИ (без изменений) ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Заполните все поля"}), 400
    hashed = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
        return jsonify({"success": True, "message": "Регистрация успешна"}), 201
    except Exception:
        return jsonify({"error": "Пользователь уже существует"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    with get_db_connection() as conn:
        user = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if user and check_password_hash(user['password_hash'], password):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({"success": True, "token": token, "username": username})
    return jsonify({"error": "Неверный логин или пароль"}), 401

# --- ЭНДПОИНТЫ ДЛЯ СОХРАНЕНИЯ/ЗАГРУЗКИ ПРОМПТОВ (без изменений, кроме импорта get_db_connection) ---
@app.route('/api/save_prompt', methods=['POST'])
@token_required
def save_prompt(current_user_id):
    data = request.json
    p_type = data.get('type')
    inp = data.get('input')
    out = data.get('output')
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO saved_prompts (user_id, prompt_type, input_text, output_text) VALUES (?, ?, ?, ?)",
            (current_user_id, p_type, inp, out)
        )
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/get_last_prompts', methods=['GET'])
@token_required
def get_last_prompts(current_user_id):
    result = {"positive": None, "negative": None}
    with get_db_connection() as conn:
        pos = conn.execute(
            "SELECT input_text, output_text FROM saved_prompts WHERE user_id = ? AND prompt_type = 'positive' ORDER BY created_at DESC LIMIT 1",
            (current_user_id,)
        ).fetchone()
        if pos:
            result["positive"] = {"input": pos['input_text'], "output": pos['output_text']}
        neg = conn.execute(
            "SELECT input_text, output_text FROM saved_prompts WHERE user_id = ? AND prompt_type = 'negative' ORDER BY created_at DESC LIMIT 1",
            (current_user_id,)
        ).fetchone()
        if neg:
            result["negative"] = {"input": neg['input_text'], "output": neg['output_text']}
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user_id):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT prompt_type, input_text, output_text, created_at FROM saved_prompts WHERE user_id = ? ORDER BY created_at DESC",
            (current_user_id,)
        ).fetchall()
    return jsonify([dict(row) for row in rows])

# --- НОВЫЙ ЭНДПОИНТ: ГЕНЕРАЦИЯ ПРОМПТА (СЛОВАРЬ + ИИ) ---
@app.route('/api/build_prompt', methods=['POST'])
def build_prompt_endpoint():
    data = request.json
    user_input = data.get('userInput')
    model_key = data.get('modelKey', 'default')
    locale = data.get('locale', 'ru')
    auto_learn = data.get('auto_learn', False)
    
    if not user_input:
        return jsonify({"error": "userInput required"}), 400
    
    prompt_text, source = build_prompt(user_input, model_key, locale, auto_learn)
    return jsonify({
        "prompt": prompt_text,
        "source": source,
        "model": model_key
    })

# --- (Опционально) Админский эндпоинт для ручного пополнения словаря ---
@app.route('/api/admin/refresh_dictionary', methods=['POST'])
@token_required
def admin_refresh(current_user_id):
    # Здесь можно проверить, что пользователь — администратор (например, по username)
    # Пока просто перезагружает начальные данные (осторожно!)
    # В реальном проекте лучше сделать отдельную таблицу admin_roles.
    with get_db_connection() as conn:
        # Очистка таблиц словаря и повторная загрузка
        conn.execute("DELETE FROM category_localized")
        conn.execute("DELETE FROM categories")
        conn.execute("DELETE FROM connectors")
        conn.execute("DELETE FROM model_rules")
        # Вызов функции загрузки начальных данных (можно импортировать из database)
        from database import _load_initial_dictionary_data
        _load_initial_dictionary_data(conn.cursor())
        conn.commit()
    return jsonify({"success": True, "message": "Словарь перезагружен из резервной копии"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
