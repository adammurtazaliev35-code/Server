import os
import requests

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
