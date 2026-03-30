from flask import Flask, request, jsonify
from flask_cors import CORS  # Добавьте это, чтобы фронтенд мог достучаться до сервера
import os
import requests

app = Flask(__name__)
CORS(app) # Разрешаем запросы с вашего сайта

# --- БАЗА ЗНАНИЙ ПО МОДЕЛЯМ (Model-Specific Hints) ---
MODEL_GUIDES = {
    "gpt-4o": "Use Markdown for hierarchy. Focus on 'Chain of Thought'. Use system roles like 'Act as [Role]'.",
    "claude-3.5-sonnet": "Structure instructions using XML tags (e.g., <instructions>, <context>). Claude prefers clear separation of data and tasks.",
    "gemini-2.0-pro": "Provide clear examples (few-shot). Gemini responds well to 'Instruction: ' and 'Constraint: ' labels.",
    "deepseek-v3": "Be extremely precise with technical requirements. Use step-by-step logic and explicit constraints.",
    "dalle-3": "Focus on lighting, composition, medium (oil, photo), and art style. Avoid negative words; describe what SHOULD be there.",
    "midjourney": "Use descriptive keywords separated by commas. Add parameters like --ar 16:9 or --stylize at the end."
}

def refine_prompt_logic(user_input, target_model, use_instructions):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # Подготовка подсказки для самого Gemini (как он должен улучшить промпт)
    system_instruction = f"""
    You are an expert Prompt Engineer. Your task is to transform a raw user request into a high-quality, professional prompt.
    Target Model: {target_model}
    
    Rules:
    1. Improve clarity, detail, and professional vocabulary.
    2. If the user put text in quotes "" or parentheses (), treat those as strict instructions/constraints.
    3. If 'use_instructions' is TRUE, you MUST return the result in two clear sections: 
       - 'PROMPT': The refined main request.
       - 'INSTRUCTIONS': A list of specific constraints AND technical tips for {target_model} (based on: {MODEL_GUIDES.get(target_model, 'general optimization')}).
    4. Return ONLY the improved text, no conversational preamble.
    """

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": f"Refine this prompt. Use_instructions={use_instructions}. Input: {user_input}"}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 2048}
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/api/refine', methods=['POST'])
def refine():
    data = request.get_json()
    user_prompt = data.get('prompt', '')
    target_model = data.get('model', 'gpt-4o')
    use_instructions = data.get('use_instructions', False)

    if not user_prompt:
        return jsonify({"error": "Prompt is empty"}), 400

    refined_text = refine_prompt_logic(user_prompt, target_model, use_instructions)
    
    return jsonify({"refined_prompt": refined_text})

@app.route('/', methods=['GET'])
def home():
    return "Prompt Refiner API is Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
