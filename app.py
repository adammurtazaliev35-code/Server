from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

# Your existing SCENARIOS config (Keep it exactly as is)
SCENARIOS = {
    "general": {
        "name": "💬 Обычный чат",
        "temperature": 0.7,
        "max_tokens": 1024,
        "welcome_message": "Здравствуйте! Я ваш ИИ помощник...",
        "system_prompt": "Ты - полезный AI ассистент. Отвечай на русском языке..."
    },
    # ... other scenarios ...
     "tech": {
        "name": "🔧 Технический помощник", 
        "temperature": 0.3,
        "max_tokens": 2048,
        "welcome_message": "...",
        "system_prompt": "Ты - технический эксперт..."
    },
    "creative": {
        "name": "🎨 Креативный режим",
        "temperature": 0.9,
        "max_tokens": 1536,
        "welcome_message": "...",
        "system_prompt": "Ты - креативный писатель..."
    },
    "ideas": {
        "name": "💡 Генератор идей",
        "temperature": 0.8,
        "max_tokens": 1024,
        "welcome_message": "...",
        "system_prompt": "Ты - специалист по генерации идей..."
    }
}

def get_ai_response(history, scenario="general", temp_override=None, tokens_override=None):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    config = SCENARIOS.get(scenario, SCENARIOS["general"])
    
    # LOGIC: Use slider value if provided, otherwise use default
    final_temp = float(temp_override) if temp_override is not None else config["temperature"]
    final_tokens = int(tokens_override) if tokens_override is not None else config["max_tokens"]

    # IMPROVEMENT: Use the official 'system_instruction' field
    payload = {
        "system_instruction": {
            "parts": [{"text": config["system_prompt"]}]
        },
        "contents": history, # We now pass the full history list
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
            return "Error: No response from AI"
    except Exception as e:
        print(f"API Error: {e}")
        return f"Error connecting to AI: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    
    # The app can now send a 'history' array OR just a 'message'
    # If sending 'history', it should look like: 
    # [{"role": "user", "parts": [{"text": "Hi"}]}, {"role": "model", "parts": [{"text": "Hello"}]}]
    history = data.get('history', [])
    message = data.get('message', '')
    scenario = data.get('scenario', 'general')
    
    # Slider inputs
    temp = data.get('temperature')
    tokens = data.get('max_tokens')

    # If there is no history but there is a message, start a new history
    if not history and message:
        history = [{"role": "user", "parts": [{"text": message}]}]
    elif message:
        # Append current message to existing history
        history.append({"role": "user", "parts": [{"text": message}]})

    if not history:
         return jsonify({"error": "No message or history provided"}), 400

    # Commands logic (Optional: You can keep your command logic here if you want)
    
    ai_text = get_ai_response(history, scenario, temp, tokens)

    return jsonify({
        "response": ai_text,
        "scenario": scenario
    })

# ... Keep your other routes (welcome, scenarios, etc.) ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
