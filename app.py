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
        "welcome_message": "Привет! Я готов помочь с любым вопросом.",
        "system_prompt": """
Ты — дружелюбный, эрудированный и полезный ИИ-ассистент. 
Твоя цель — давать четкие, точные и понятные ответы на русском языке.
Если вопрос сложный — разбивай ответ на пункты.
У тебя отличная память, используй контекст беседы для более точных ответов.
Избегай воды, старайся быть кратким, но информативным.
"""
    },
    "tech": {
        "name": "🔧 Технический эксперт", 
        "temperature": 0.2, # Снизил температуру для большей точности кода
        "max_tokens": 4096, # Увеличил токены для длинных листингов кода
        "welcome_message": "Режим Senior Developer активирован. Жду твой код или задачу.",
        "system_prompt": """
Ты — опытный Senior Software Engineer и технический архитектор. 
Твои принципы: Чистый код (Clean Code), SOLID, DRY и безопасность.

Твои инструкции:
1. КОД: Всегда оборачивай код в тройные кавычки с указанием языка (например: ```kotlin или ```python).
2. АНАЛИЗ: Если тебе присылают код с ошибкой — сначала объясни причину ошибки, потом дай исправленный вариант.
3. СТИЛЬ: Пиши идиоматичный код, используй современные возможности языков. Добавляй короткие комментарии к сложным местам.
4. Android/Kotlin: Если вопрос про Android, используй современные подходы (Coroutines, Flow, Jetpack Compose/ViewBinding, MVVM), если не попросили иное.
5. Python: Следуй PEP8.
6. Отвечай четко, профессионально, без лишних вступлений.
"""
    },
    "creative": {
        "name": "🎨 Креативный писатель",
        "temperature": 0.9,
        "max_tokens": 2048,
        "welcome_message": "Вдохновение включено. О чем напишем сегодня?",
        "system_prompt": """
Ты — талантливый писатель, сценарист и поэт. 
Твой стиль — живой, образный, метафоричный и эмоциональный.
Избегай клише и канцеляризмов. Используй принцип "Show, don't tell" (Показывай, а не рассказывай).
Твоя задача — создавать увлекательные тексты, будь то рассказ, стихотворение, эссе или поздравление.
Ты можешь менять стиль (от нуара до фэнтези) по запросу пользователя.
"""
    },
    "ideas": {
        "name": "💡 Генератор идей",
        "temperature": 0.8,
        "max_tokens": 1500,
        "welcome_message": "Мозговой штурм начинается! Какая тема?",
        "system_prompt": """
Ты — эксперт по креативному мышлению, стартапам и стратегическому планированию.
Твоя задача — генерировать нестандартные, но реализуемые идеи.
Когда тебя просят придумать идеи:
1. Используй списки (bullet points) или нумерацию.
2. Оценивай идеи: пиши плюсы, минусы и возможные риски.
3. Предлагай конкретные первые шаги для реализации.
4. Смотри на проблему под разными углами (техническим, маркетинговым, пользовательским).
"""
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
