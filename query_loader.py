# query_loader.py

import json
from pathlib import Path

TEMPLATE_PATH = Path("query_templates.json")


def load_templates() -> dict[str, dict[str, str]] | dict:
    '''Load SQL query templates from the JSON file. Returns an empty dictionary
    if the file does not exist.
    '''
    if TEMPLATE_PATH.exists():
        with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_templates(templates: dict[str, dict[str, str]]) -> None:
    '''Save the given SQL query templates to the JSON file.'''
    with TEMPLATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def get_query(name: str) -> tuple[str, str, list[str] | None]:
    '''Retrieve the description, SQL text, and optional headers
    for a given template name.
    '''
    templates = load_templates()
    entry = templates.get(name)
    if entry:
        return entry.get("description", ""), entry.get("query", ""),\
            entry.get("headers")
    return "", "", None


def choose_template() -> str | None:
    '''
    Launch an interactive menu to select, add, edit, or delete SQL query
    templates. Returns the name of the selected template or None on exit.'''
    while True:
        templates = list_templates()
        print("\nAvaiable query templates:")
        for i, (name, desc) in enumerate(templates.items(), start=1):
            print(f"{i}. {name} – {desc}")
        print('0. Default query (basic_stats)')
        print('\033[2;36ma - add/edit template')
        print('d - delete template\033[0m')
        selection = input("Select : ").strip()
        if selection:
            try:
                if selection in 'Qq':
                    return None
                elif selection == '0':
                    name = 'basic_stats'
                elif selection.isdigit():
                    index = int(selection) - 1
                    name = list(templates.keys())[index]
                elif selection in 'Aa':
                    add_template()
                elif selection in 'Dd':
                    delete_template()
            except Exception:
                print("Wrong choise.")
                continue

            if not name:
                continue
            return name


def list_templates() -> dict[str, str]:
    '''Return a dictionary of template names and their descriptions.'''
    templates = load_templates()
    return {key: val["description"] for key, val in templates.items()}


def add_template() -> None:
    '''Interactively add a new SQL query template, or edit an existing one
    if the name already exists
    '''
    name: str = input('Template name? ')
    if not name:
        print('Cancel')
        return None
    templates = load_templates()
    if name in templates:
        option = input('Query name already exists,\
 do you want to edit it? ("Y"/any)\n')
        if option and option in 'Yy':
            description, query = interactive_edit(name, templates)
            save_templates(templates)
            print('Query template updated\n')
            return None
        else:
            print('Canceled\n')
            return None
    description = input('Description: \n')
    query = input('Query: \n')
    if not query:
        print('Empty query. Cancel')
        return None
    templates[name] = {
        "description": description,
        "query": query
    }
    save_templates(templates)
    print('Query template added\n')
    return None


def delete_template() -> None:
    '''Delete a template by name after user confirmation.'''
    name: str = input('Template name? ')
    if not name:
        print('Cancel')
        return None
    templates = load_templates()
    if name in templates:
        action = input(
            f'Do you realy want to delete "{name}" template? (Y/N)\n')
        if action in 'Yy':
            del templates[name]
            save_templates(templates)
            print(f"'{name}' deleted.")
            return None
        else:
            return None
    print(f'"{name}" not found.')
    return None


def interactive_edit(
    name: str,
    templates: dict[str, dict[str, str]]
) -> tuple[str, str]:
    '''Interactively edit an existing SQL query and its description. Returns
    the new description and query string.'''
    current_query = templates[name]["query"]
    current_description = templates[name]['description']
    print(f"Current template: '{name}':")
    print("-" * 40)
    print(current_query)
    print("-" * 40)
    print("Type  new query. An empty line ends the input:")

    new_lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        new_lines.append(line)

    if not new_lines:
        print("Edit canceled: empty input.")
        return current_query, current_description

    new_query = " ".join(new_lines)
    print(f'Current description: {current_description}\n')
    if input('Do you want to edit it? ("y"/any)\n') in 'Yy':
        new_description = input()
    else:
        new_description = current_description
    return new_description, new_query
