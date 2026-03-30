from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from models_config import MODELS_CONFIG # Импортируем нашу библиотеку

app = Flask(__name__)
CORS(app)

# --- ГЛАВНАЯ ИНСТРУКЦИЯ ДЛЯ GEMINI (ДВИЖОК УЛУЧШЕНИЯ) ---
PROMPT_ENGINEER_SYSTEM_PROMPT = """
Ты — ведущий эксперт по промпт-инжинирингу. Твоя задача: взять сырые идеи пользователя и превратить их в высокоэффективные промпты.

ТВОЙ АЛГОРИТМ РАБОТЫ:
1. Анализ ввода: Найди суть запроса. Если в тексте есть слова в "кавычках" или (скобках), это КРИТИЧЕСКИЕ ИНСТРУКЦИИ, которые нельзя менять, их нужно выделить.
2. Применение знаний о модели: Тебе будет дана целевая модель. Используй её специфические правила (Style Guide) для форматирования.
3. Улучшение: Сделай текст более профессиональным, детальным и понятным для ИИ.

ФОРМАТ ОТВЕТА (Если параметр USE_INSTRUCTIONS = True):
Ты ДОЛЖЕН разделить ответ на два четких блока:
---
PROMPT:
[Здесь только сам улучшенный текст промпта]

INSTRUCTIONS:
[Здесь список технических команд, параметров и правил для конкретной модели]
---

Если USE_INSTRUCTIONS = False, верни один монолитный, но идеально структурированный промпт.
НИКАКИХ вступлений вроде "Вот ваш промпт". Только результат.
"""

def get_refined_prompt(user_text, target_model_id, use_instructions):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Получаем специфические настройки для выбранной модели
    model_info = MODELS_CONFIG.get(target_model_id, {"style_guide": "General optimization"})
    
    # Формируем запрос для Gemini
    payload = {
        "system_instruction": {
            "parts": [{"text": PROMPT_ENGINEER_SYSTEM_PROMPT}]
        },
        "contents": [{
            "role": "user", 
            "parts": [{
                "text": f"""
                TARGET MODEL: {target_model_id}
                STYLE GUIDE: {model_info['style_guide']}
                USE_INSTRUCTIONS_BLOCK: {use_instructions}
                
                USER INPUT: {user_text}
                """
            }]
        }],
        "generationConfig": {
            "temperature": 0.4, # Ниже температура — выше точность промпта
            "maxOutputTokens": 2048
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error on Server: {str(e)}"

@app.route('/api/refine', methods=['POST'])
def refine():
    data = request.get_json()
    
    # Извлекаем данные из фронтенда
    raw_prompt = data.get('prompt', '')
    model_id = data.get('model', 'gpt-4o')
    is_instruct = data.get('use_instructions', False)

    if not raw_prompt:
        return jsonify({"error": "Empty prompt"}), 400

    # Запускаем процесс улучшения
    result = get_refined_prompt(raw_prompt, model_id, is_instruct)

    return jsonify({"refined_prompt": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
