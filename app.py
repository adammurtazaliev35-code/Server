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
        "system_prompt": """Ты - полезный AI ассистент. Отвечай на русском языке.
Будь дружелюбным, поддерживающим и помогай с различными вопросами."""
    },
    "tech": {
        "name": "🔧 Технический помощник", 
        "temperature": 0.3,
        "max_tokens": 2048,
        "system_prompt": """Ты - технический эксперт. Давай точные, структурированные ответы.
Объясняй сложные концепции простыми словами. Будь внимателен к деталям."""
    },
    "creative": {
        "name": "🎨 Креативный режим",
        "temperature": 0.9,
        "max_tokens": 1536,
        "system_prompt": """Ты - креативный писатель и генератор идей. 
Будь оригинальным, вдохновляющим и нестандартным. 
Предлагай необычные решения и творческие подходы."""
    },
    "ideas": {
        "name": "💡 Генератор идей",
        "temperature": 0.8,
        "max_tokens": 1024,
        "system_prompt": """Ты - специалист по генерации идей. 
Помогай придумывать новые концепции, проекты и решения.
Предлагай несколько вариантов и развивай мысли."""
    }
}

# Текущий сценарий по умолчанию
current_scenario = "general"

def get_ai_response(message, scenario="general"):
    api_key = os.getenv("GEMINI_API_KEY")
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
        return f"Извините, произошла ошибка: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    global current_scenario
    
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
                current_scenario = command
                scenario_info = SCENARIOS[command]
                return jsonify({
                    "response": f"✅ Режим изменен на: {scenario_info['name']}\n\n{scenario_info['system_prompt']}",
                    "scenario": command,
                    "scenario_name": scenario_info["name"]
                })
            else:
                available_commands = ", ".join([f"/{key}" for key in SCENARIOS.keys()])
                return jsonify({
                    "response": f"❌ Неизвестная команда. Доступные команды:\n{available_commands}",
                    "scenario": current_scenario
                })
        
        # Используем переданный сценарий или текущий
        response = get_ai_response(message, scenario)
        
        return jsonify({
            "response": response,
            "scenario": scenario,
            "scenario_name": SCENARIOS[scenario]["name"]
        })
        
    except Exception as e:
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """Возвращает список доступных сценариев"""
    scenarios_list = {key: value["name"] for key, value in SCENARIOS.items()}
    return jsonify({"scenarios": scenarios_list})

@app.route('/api/current_scenario', methods=['GET'])
def get_current_scenario():
    """Возвращает текущий активный сценарий"""
    return jsonify({
        "scenario": current_scenario,
        "scenario_name": SCENARIOS[current_scenario]["name"]
    })

@app.route('/')
def home():
    return jsonify({
        "message": "AI Chat Server with Scenarios is running!",
        "status": "active",
        "model": "Gemini 2.0 Flash",
        "current_scenario": SCENARIOS[current_scenario]["name"],
        "endpoint": "POST /api/chat",
        "scenarios_endpoint": "GET /api/scenarios"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
