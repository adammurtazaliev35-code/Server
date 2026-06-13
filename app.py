from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import jwt
from functools import wraps
from yandex_ai import init_yandex_gpt
import os

from database import init_db, get_db_connection
from prompt_builder import build_prompt

app = Flask(__name__)
CORS(app)

YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY')
YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID')
if YANDEX_API_KEY and YANDEX_FOLDER_ID:
    init_yandex_gpt(YANDEX_API_KEY, YANDEX_FOLDER_ID)
    print("YandexGPT инициализирован успешно")
else:
    print("YandexGPT не настроен: проверьте переменные окружения YANDEX_API_KEY и YANDEX_FOLDER_ID")
    
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret-key-for-local-pc-launch-default')

# Инициализируем БД 
init_db()

# --- ДЕКОРАТОР JWT ---
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

def token_optional(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user_id = None
        
        # Проверяем, прислал ли клиент заголовок Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
                try:
                    # Пытаемся расшифровать токен
                    data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                    current_user_id = data['user_id']
                except Exception:
                    # Если токен неверный или истек, мы не выдаем ошибку 401, 
                    # а просто считаем пользователя гостем
                    current_user_id = None
                    
        # Передаем id (число или None) в функцию эндпоинта
        return f(current_user_id, *args, **kwargs)
    return decorated
# --- ЭНДПОИНТЫ АВТОРИЗАЦИИ ---
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

# --- ЭНДПОИНТЫ ДЛЯ СОХРАНЕНИЯ/ЗАГРУЗКИ ---
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

# --- НОВЫЙ ЭНДПОИНТ: ГЕНЕРАЦИЯ ПРОМПТА ---
@app.route('/api/build_prompt', methods=['POST'])
@token_optional
def build_prompt_endpoint(current_user_id):
    data = request.json
    user_input = data.get('userInput')
    model_key = data.get('modelKey', 'default')
    locale = data.get('locale', 'ru')
    auto_learn = data.get('auto_learn', False)
    use_instructions = data.get('use_instructions', False) # Извлекаем параметр

    if not user_input:
        return jsonify({"error": "userInput required"}), 400

    prompt_text, source = build_prompt(user_input, model_key, locale, auto_learn, use_instructions)
    
    return jsonify({
        "prompt": prompt_text,
        "source": source,
        "model": model_key
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
