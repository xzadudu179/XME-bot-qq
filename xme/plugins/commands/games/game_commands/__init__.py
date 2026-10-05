from . import guess_num
from . import wordle

games = {
    guess_num.game_meta['name']: {
        "func": guess_num.play_game,
        "meta": guess_num.game_meta
    },
    wordle.game_meta['name']: {
        "func": wordle.play_game,
        "meta": wordle.game_meta
    },
}
