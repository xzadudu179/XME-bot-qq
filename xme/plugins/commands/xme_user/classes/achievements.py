from xme.xmetools.jsontools import read_from_path


def get_achievements() -> dict:
    return read_from_path("./static/achievements.json")

def has_achievement(achievement_name):
    achievements = get_achievements()
    if achievement_name not in achievements.keys():
        return False
    return True

def get_achievement_details(achievement_name: str, achieved: bool = False, achieved_time="", achieved_from=""):
    achievements = get_achievements()
    if achievement_name not in achievements.keys():
        raise ValueError(f"没有名为 \"{achievement_name}\" 的成就")
    achievement = achievements[achievement_name]
    from xme.plugins.commands.xme_user.classes.user import coin_pronoun, coin_name
    msg = f"[{'隐藏' if achievement['hidden'] else ''}成就] {achievement_name}{' (已达成)' if achieved else ''}\n条件: {achievement['desc'].format(coin_name=coin_name, coin_pronoun=coin_pronoun)}\n奖励: {achievement['award']} {coin_pronoun}{coin_name}"
    archieved_suffix = ''
    if achieved:
        archieved_suffix = f'\n达成时间: {achieved_time}\n达成地点: {achieved_from}'
    return msg + archieved_suffix