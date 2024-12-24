from . import guess_num

games = {
    guess_num.game_meta['name']: {
        "func": guess_num.play_game,
        "meta": guess_num.game_meta
    }
}