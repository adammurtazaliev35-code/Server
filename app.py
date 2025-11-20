from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

# --- CONFIGURATION ---
SCENARIOS = {
    "general": {
        "name": "💬 Обычный чат",
        "temperature": 0.7,
        "max_tokens": 1024,
        "welcome_message": "Здравствуйте! Я ваш ИИ помощник...",
        "system_prompt": "Ты - полезный AI ассистент. У тебя отличная память, ты помнишь весь контекст нашей беседы. Отвечай на русском языке."
    },
    "tech": {
        "name": "🔧 Технический помощник", 
        "temperature": 0.3,
        "max_tokens": 2048,
        "welcome_message": "Готов к отладке кода.",
        "system_prompt": "Ты - технический эксперт и программист. Анализируй код, ищи ошибки и предлагай оптимизацию."
    },
    "creative": {
        "name": "🎨 Креативный режим",
        "temperature": 0.9,
        "max_tokens": 1536,
        "welcome_message": "Давай творить!",
        "system_prompt": "Ты - креативный писатель. Используй богатый язык, метафоры и нестандартные идеи."
    },
    "ideas": {
        "name": "💡 Генератор идей",
        "temperature": 0.8,
        "max_tokens": 1024,
        "welcome_message": "Нужны идеи?",
        "system_prompt": "Ты - специалист по мозговому штурму. Предлагай списки идей, концепции и стратегии."
    }
}

def get_ai_response(history, scenario="general", temp_override=None, tokens_override=None):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    config = SCENARIOS.get(scenario, SCENARIOS["general"])
    
    final_temp = float(temp_override) if temp_override is not None else config["temperature"]
    final_tokens = int(tokens_override) if tokens_override is not None else config["max_tokens"]

    payload = {
        "system_instruction": {
            "parts": [{"text": config["system_prompt"]}]
        },
        "contents": history, 
        "generationConfig": {
            "temperature": final_temp,
            "maxOutputTokens": final_tokens,
            "topP": 0.95,
            "topK": 40
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"AI Error Response: {result}") # Лог ошибки от Google
            return "Error: Empty response from AI"
    except Exception as e:
        print(f"API Connection Error: {e}")
        return f"Error connecting to AI: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    
    # 1. Читаем данные
    history = data.get('history', [])
    message = data.get('message', '')
    scenario = data.get('scenario', 'general')
    temp = data.get('temperature')
    tokens = data.get('max_tokens')

    # 2. ЛОГИРОВАНИЕ (Смотри в консоль сервера!)
    print(f"\n--- NEW REQUEST ---")
    print(f"Scenario: {scenario}")
    print(f"Received 'history' length: {len(history)}") # Сколько сообщений пришло
    print(f"Received 'message': {message}")
    
    # 3. Логика обработки
    # Если пришел список history - используем его.
    # Если history пустой, но есть message (старая версия клиента) - создаем новый список.
    if not history and message:
        print("⚠️ WARNING: Using fallback (Message only mode)")
        history = [{"role": "user", "parts": [{"text": message}]}]
    elif message:
        # Если зачем-то прислали и то и то, добавляем сообщение в конец
        # Но твой новый Android код message не шлет, так что этот блок не должен срабатывать
        print("⚠️ Adding message to existing history")
        history.append({"role": "user", "parts": [{"text": message}]})

    if not history:
         return jsonify({"error": "No message or history provided"}), 400

    # Для отладки: выводим последнее сообщение, которое уйдет в ИИ
    if len(history) > 0:
        print(f"Sending {len(history)} messages to Gemini. Last one: {history[-1]}")

    # 4. Запрос
    ai_text = get_ai_response(history, scenario, temp, tokens)

    return jsonify({
        "response": ai_text,
        "scenario": scenario
    })

@app.route('/', methods=['GET'])
def home():
    return "AI Server is Running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
