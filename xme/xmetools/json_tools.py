import json

def read_from_path(path) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except:
        return {}

def save_to_path(path, data, ensure_ascii=False, indent: int | str | None=None):
    with open(path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent))