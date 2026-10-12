"""Provider capabilities are independent of TREN memory and scheduling."""
PROVIDERS = {
    'ollama': {'name': 'Ollama', 'capabilities': ['conversation', 'web_research']},
    'codex': {'name': 'Codex / ChatGPT login', 'capabilities': ['coding', 'code_review']},
}


def coding_intent(text):
    import re
    return text.startswith('/code ') or bool(re.search(
        r'\b(create|build|write|fix|implement|debug|refactor)\b.*\b(python|application|app|code|script|website|program|bug)\b',
        text, re.I))
