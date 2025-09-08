# 道具
class Tool:
    from .player import Player
    def __init__(self, name: str, desc: str, player: Player, changes: dict):
        self.name = name
        self.desc = desc
        self.player = player
        self.changes = changes

    def __str__(self):
        return f"{self.name}: {self.desc}"

    def apply(self) -> str:
        return self.player.change_attr(self.changes)
