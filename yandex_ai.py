import os
import requests
import json
from typing import Optional

class YandexGPTClient:
    def __init__(self, api_key: str, folder_id: str, model: str = "yandexgpt"):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json"
        }

    def generate_prompt(self, user_input: str, model_key: str, locale: str = 'ru', use_instructions: bool = False) -> Optional[str]:
            # 1. Извлекаем инструкции, если они есть в кавычках/скобках
            import re
            # Ищем текст в "" или ()
            instructions = re.findall(r'["\'\(](.*?)["\'\)]', user_input)
            
            # Очищаем основной запрос от того, что мы вытащили как инструкции
            clean_prompt = re.sub(r'["\'\(].*?["\'\)]', '', user_input).strip()
            
            # 2. Формируем текст инструкций для ИИ
            instruction_text = ", ".join(instructions) if (use_instructions and instructions) else "нет дополнительных инструкций"
    
            # 3. Системный промпт (строго для ИИ-редактора)
            system_prompt = (
                f"Ты — эксперт по созданию промптов. "
                f"Твоя задача: улучшить промпт для модели {model_key}. "
                f"Пользовательский запрос: {clean_prompt}. "
                f"Инструкции к промпту: {instruction_text}. "
                f"Сформируй итоговый, структурированный промпт, пригодный для прямой вставки в LLM. "
                f"Отвечай только текстом промпта, без лишних пояснений."
            )
    
            body = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}",
                "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 500},
                "messages": [
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": "Сгенерируй финальный промпт"}
                ]
            }

# Глобальный экземпляр клиента (будет инициализирован в app.py)
yandex_client: Optional[YandexGPTClient] = None

def init_yandex_gpt(api_key: str, folder_id: str):
    global yandex_client
    yandex_client = YandexGPTClient(api_key, folder_id)

def generate_with_ai(user_input: str, model_key: str, locale: str = 'ru', use_instructions: bool = False) -> Optional[str]:
    if yandex_client is None:
        print("YandexGPT клиент не инициализирован")
        return None
    return yandex_client.generate_prompt(user_input, model_key, locale, use_instructions)
