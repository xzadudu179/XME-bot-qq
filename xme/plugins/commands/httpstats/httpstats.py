import json

def httpstats(state):
    with open(f'./xme/plugins/commands/httpstats/HttpStats.json', 'r', encoding='utf-8') as file:
        return json.load(file).get(state, None)