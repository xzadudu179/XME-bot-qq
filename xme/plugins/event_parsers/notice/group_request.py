from nonebot import on_request, RequestSession
import config
from ....xmetools import color_manage as c

# 将函数注册为群请求处理器
@on_request('group')
async def _(session: RequestSession):
    # 判断验证信息是否符合要求
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"有新的群聊请求哦: {session.event}"))
    print(session.event.user_id)
    if session.event.user_id in config.SUPERUSERS:
        # 验证信息正确，同意入群
        print("同意入群")
        await session.approve()
        return
    # 验证信息错误，拒绝入群
    print("拒绝入群")
    # await session.send('唔，我只能被 SUPERUSERS 拉进群哦')
    await session.reject('唔，我只能被 SUPERUSERS 拉进群哦')