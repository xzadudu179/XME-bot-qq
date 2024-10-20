from nonebot import on_notice, NoticeSession

# 将函数注册为群成员增加通知处理器
@on_notice('group_increase')
async def _(session: NoticeSession):
    # 发送欢迎消息
    await session.send(f'欢迎 [CQ:at,qq={session.event.user_id}] 进群（？')