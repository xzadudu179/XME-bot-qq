from .tool import Tool

# 出发基地
class Base:
    def __init__(
            self,
            base_id,
            name,
            tools: list[Tool]
        ):
        self.id = base_id
        self.name = name
        self.tools = tools