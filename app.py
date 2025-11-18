from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

# Конфигурации сценариев
SCENARIOS = {
    "general": {
        "name": "💬 Обычный чат",
        "temperature": 0.7,
        "max_tokens": 1024,
        "welcome_prompt": "Представься как полезный AI ассистент и предложи помощь с любыми вопросами. Будь дружелюбным и приветливым.",
        "system_prompt": "Ты - полезный AI ассистент. Отвечай на русском языке. Будь дружелюбным, поддерживающим и помогай с различными вопросами."
    },
    "tech": {
        "name": "🔧 Технический помощник", 
        "temperature": 0.3,
        "max_tokens": 2048,
        "welcome_prompt": "Представься как технический эксперт. Объясни, что можешь помочь с кодом, техническими проблемами и объяснением сложных концептов.",
        "system_prompt": "Ты - технический эксперт. Давай точные, структурированные ответы. Объясняй сложные концепции простыми словами. Будь внимателен к деталям."
    },
    "creative": {
        "name": "🎨 Креативный режим",
        "temperature": 0.9,
        "max_tokens": 1536,
        "welcome_prompt": "Представься как креативный помощник. Расскажи о своих творческих возможностях и предложи помощь с генерацией идей, написанием текстов и художественными проектами.",
        "system_prompt": "Ты - креативный писатель и генератор идей. Будь оригинальным, вдохновляющим и нестандартным. Предлагай необычные решения и творческие подходы."
    },
    "ideas": {
        "name": "💡 Генератор идей",
        "temperature": 0.8,
        "max_tokens": 1024,
        "welcome_prompt": "Представься как специалист по генерации идей. Объясни, что можешь помочь придумывать новые концепции, проекты и нестандартные решения.",
        "system_prompt": "Ты - специалист по генерации идей. Помогай придумывать новые концепции, проекты и решения. Предлагай несколько вариантов и развивай мысли."
    }
}

def get_ai_response(message, scenario="general"):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ Ошибка: API ключ не настроен"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Получаем настройки для выбранного сценария
    config = SCENARIOS.get(scenario, SCENARIOS["general"])
    
    # Форматируем промпт с системной инструкцией
    full_prompt = f"{config['system_prompt']}\n\nПользователь: {message}"
    
    data = {
        "contents": [{
            "parts": [{
                "text": full_prompt
            }]
        }],
        "generationConfig": {
            "temperature": config["temperature"],
            "maxOutputTokens": config["max_tokens"],
            "topP": 0.95,
            "topK": 40
        }
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "Не удалось получить ответ от ИИ"
            
    except Exception as e:
        return f"❌ Ошибка подключения: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        scenario = data.get('scenario', 'general')
        
        if not message:
            return jsonify({"error": "Сообщение не может быть пустым"}), 400
        
        # Проверяем команды смены сценария
        if message.startswith('/'):
            command = message[1:].lower().strip()
            if command in SCENARIOS:
                scenario_info = SCENARIOS[command]
                welcome_response = get_ai_response(scenario_info["welcome_prompt"], command)
                return jsonify({
                    "response": f"✅ Режим изменен на: {scenario_info['name']}\n\n{welcome_response}",
                    "scenario": command,
                    "scenario_name": scenario_info["name"]
                })
            else:
                available_commands = ", ".join([f"/{key}" for key in SCENARIOS.keys()])
                return jsonify({
                    "response": f"❌ Неизвестная команда. Доступные команды:\n{available_commands}",
                    "scenario": scenario
                })
        
        # Обычный запрос к ИИ
        response = get_ai_response(message, scenario)
        
        return jsonify({
            "response": response,
            "scenario": scenario,
            "scenario_name": SCENARIOS[scenario]["name"]
        })
        
    except Exception as e:
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/api/welcome', methods=['POST'])
def welcome():
    """Генерирует приветственное сообщение для нового чата"""
    try:
        data = request.get_json()
        scenario = data.get('scenario', 'general')
        
        config = SCENARIOS.get(scenario, SCENARIOS["general"])
        welcome_response = get_ai_response(config["welcome_prompt"], scenario)
        
        return jsonify({
            "response": welcome_response,
            "scenario": scenario,
            "scenario_name": config["name"]
        })
        
    except Exception as e:
        return jsonify({"error": f"Ошибка генерации приветствия: {str(e)}"}), 500

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """Возвращает список доступных сценариев"""
    scenarios_list = {key: value["name"] for key, value in SCENARIOS.items()}
    return jsonify({"scenarios": scenarios_list})

@app.route('/')
def home():
    return jsonify({
        "message": "AI Chat Server with Scenarios is running!",
        "status": "active",
        "model": "Gemini 2.0 Flash",
        "available_scenarios": list(SCENARIOS.keys()),
        "endpoints": {
            "chat": "POST /api/chat",
            "welcome": "POST /api/welcome", 
            "scenarios": "GET /api/scenarios"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
