import json
import os
from database import get_db_connection
from yandex_ai import generate_with_ai

# Настройка OpenAI (если ключ задан в переменных окружения)
openai.api_key = os.environ.get("OPENAI_API_KEY", "")

def build_from_db(user_input, model_key, locale='ru'):
    """
    Собирает промпт по шаблонам из БД (аналог старой buildPrompt).
    Возвращает строку промпта или None, если нет данных.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем коннекторы
        conn_data = cursor.execute(
            "SELECT key_name, phrase FROM connectors WHERE locale = ?", (locale,)
        ).fetchall()
        conn_dict = {row['key_name']: row['phrase'] for row in conn_data}
        
        # Получаем правило модели
        rule_row = cursor.execute(
            "SELECT rule_text FROM model_rules WHERE model_key = ?", (model_key,)
        ).fetchone()
        if not rule_row:
            rule_row = cursor.execute("SELECT rule_text FROM model_rules WHERE model_key = 'default'").fetchone()
        model_rule = rule_row['rule_text'] if rule_row else "Будь точным и следуй инструкциям."
        
        # Загружаем все категории с локализацией
        cats = cursor.execute('''
            SELECT c.category_id, c.priority, c.keywords,
                   cl.role, cl.pos_phrases, cl.neg_phrases, cl.format_phrases
            FROM categories c
            JOIN category_localized cl ON c.category_id = cl.category_id
            WHERE cl.locale = ?
        ''', (locale,)).fetchall()
        
        # Поиск совпадений по ключевым словам
        input_lower = user_input.lower()
        matches = []
        for cat in cats:
            keywords = json.loads(cat['keywords'])
            if any(kw.lower() in input_lower for kw in keywords):
                matches.append(cat)
        if not matches:
            # fallback на категорию improve
            matches = [c for c in cats if c['category_id'] == 'improve']
        if not matches:
            return None
        
        # Сортировка по приоритету (убывание)
        matches.sort(key=lambda x: x['priority'], reverse=True)
        
        # Уникальные роли
        roles = list({match['role'] for match in matches})
        if len(roles) > 1:
            role_text = ', '.join(roles[:-1]) + (f" {('и' if locale=='ru' else 'and')} " + roles[-1])
        else:
            role_text = roles[0]
        
        # Сбор фраз из полей (массивы JSON)
        def merge_phrases(field):
            phrases = []
            for m in matches:
                arr = json.loads(m[field])
                phrases.extend(arr)
            return list(dict.fromkeys(phrases))  # уникальные
        
        pos_phrases = merge_phrases('pos_phrases')
        neg_phrases = merge_phrases('neg_phrases')
        format_phrases = merge_phrases('format_phrases')
        
        # Сборка промпта
        parts = [
            f"{conn_dict.get('intro', 'Act as')} {role_text}.",
            f"{conn_dict.get('task', 'Your main task is')} {user_input}.",
        ]
        if pos_phrases:
            parts.append(f"{conn_dict.get('style', 'While working on this')} {', '.join(pos_phrases)}.")
        if neg_phrases:
            parts.append(f"{conn_dict.get('avoid', 'strictly avoiding')} {', '.join(neg_phrases)}.")
        if format_phrases:
            parts.append(f"{conn_dict.get('ending', 'Provide the output using')} {', '.join(format_phrases)}.")
        parts.append(f"[Контекст модели]: {model_rule}")
        
        return ' '.join(parts)


def build_prompt(user_input, model_key, locale='ru', auto_learn=False, use_instructions=False):
    # 1. Пытаемся использовать ИИ
    ai_result = generate_with_ai(user_input, model_key, locale, use_instructions)
    if ai_result:
        return ai_result, "ai"
    
    # 2. Fallback на БД
    db_result = build_from_db(user_input, model_key, locale)
    if db_result:
        return db_result, "database"
    
    # 3. Абсолютный fallback
    return user_input, "fallback"
