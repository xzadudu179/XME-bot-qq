from . import Celestial, CanDevelop
# from ..faction import FACTIONS

class Station(Celestial, CanDevelop):
    """空间站类型"""
    def __init__(self, name: str, desc: str, galaxy_location, buildings=[], faction_id: int = 0, uid=None) -> None:
        Celestial.__init__(self, galaxy_location=galaxy_location, name=name, desc=desc, faction_id=faction_id, uid=uid)
        CanDevelop.__init__(self, buildings)