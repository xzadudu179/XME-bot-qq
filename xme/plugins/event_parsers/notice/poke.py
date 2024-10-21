from nonebot import on_request, RequestSession
import config
from ....xmetools import color_manage as c

@on_request("notify")
async def _(session: RequestSession):
    # 判断验证信息是否符合要求
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"有新的notify: {session}"))
    print(session.event.user_id)