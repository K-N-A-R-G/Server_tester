# query_loader.py

import json
from pathlib import Path
from typing import Dict, Optional, Any

TEMPLATE_PATH = Path("query_templates.json")


def load_templates() -> Any:
    if TEMPLATE_PATH.exists():
        with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_templates(templates: Dict[str, Dict[str, str]]) -> None:
    with TEMPLATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def get_query(name: str) -> tuple[str, Optional[list[str]]]:
    templates = load_templates()
    entry = templates.get(name)
    if entry:
        return entry.get("description", ""), entry.get("query", ""),\
         entry.get("headers")
    return "", "", None



def list_templates() -> Dict[str, str]:
    templates = load_templates()
    return {key: val["description"] for key, val in templates.items()}


def add_template(name: str, description: str, query: str) -> None:
    templates = load_templates()
    if name in templates:
        option = input('Query name already exists,\
         do you want to edit it? ("Y"/any)\n')
        if option in 'Yy':
            description, query = interactive_edit(name, templates)
            save_templates(templates)
            print('Query template updated\n')
            return None
        else:
            print('Canceled\n')
            return None
    description = input('Description: \n')
    query = input('Query: \n')
    templates[name] = {
        "description": description,
        "query": query
    }
    save_templates(templates)
    print('Query template added\n')
    return None


def delete_template(name: str) -> str:
    templates = load_templates()
    if name in templates:
        del templates[name]
        save_templates(templates)
        return f"'{name}' deleted."
    return f"'{name}' not found."


def interactive_edit(
 name: str,
 templates: Dict[str, Dict[str, str]]) -> tuple[str, str]:
    current_query = templates[name]["query"]
    current_description = templates[name]['description']
    print(f"Текущий шаблон '{name}':")
    print("-" * 40)
    print(current_query)
    print("-" * 40)
    print("Введите обновлённый запрос. Пустая строка завершает ввод:")

    new_lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        new_lines.append(line)

    if not new_lines:
        print("Редактирование отменено: пустой ввод.")
        return current_query, current_description

    new_query = " ".join(new_lines)
    print(f'Current description: {current_description}\n')
    if input('Do you want to edit it? ("y"/any)\n') in 'Yy':
        new_description = input()
    else:
        new_description = current_description
    return new_description, new_query
