from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Простой интеллектуальный чат-бот



def get_ai_response(message):
    # Ваш API-ключ, который вы установили в переменные окружения Render
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Данные для запроса в формате JSON
    data = {
        "contents": [{
            "parts": [{
                "text": message
            }]
        }]
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()  # Проверка на ошибки HTTP
        result = response.json()
        # Извлечение текста ответа из структуры JSON
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        # Обработка ошибок (например, превышение лимита, недоступность API)
        return f"Извините, произошла ошибка: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({"error": "Сообщение не может быть пустым"}), 400
        
        response = get_ai_response(message)
        return jsonify({"response": response})
        
    except Exception as e:
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/')
def home():
    return jsonify({
        "message": "AI Chat Server is running!",
        "status": "active",
        "endpoint": "POST /api/chat",
        "example": {"message": "Привет!"}
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
