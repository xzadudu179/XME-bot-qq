from functools import wraps
from ..classes.user import User
import traceback
from xme.xmetools.command_tools import send_msg
from ..classes.database import Xme_database

def pre_check(pre_func=None, end_func=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            # print("检查是否注册")
            xme_user = await check_register(session)
            if pre_func:
                print("执行首函数")
                pre_func(session)
            result = None
            try:
                result = await func(session, xme_user, *args, **kwargs)
            except TypeError:
                # 出错时尝试更新一下用户数据
                print("用户出现 TypeError")
                # update_user_data(session)
                print(xme_user)
                result = await func(session, xme_user, *args, **kwargs)
            except Exception as ex:
                print(f"出现错误：\n{traceback.format_exc()}")
                await send_msg(session, f"呜呜，执行指令出现错误:\n{ex}")
            # print(user)
            if end_func:
                print("执行尾函数")
                end_func(session)
            return result
        return wrapper
    return decorator

# def update_user_data(session):
#     database = Xme_database()
#     user_id = session.event.user_id
#     user: User = User.load_by_id(database, user_id)
#     user.update()

def save_data(session):
    database = Xme_database()
    user_id = session.event.user_id
    users = User.load_by_id(database, user_id)
    user: User = users[0]
    user.save()
    print("用户数据保存成功.")

async def check_register(session):
    print("检查是否注册")
    database = Xme_database()
    user_id = session.event.user_id
    user = User.load_by_id(database, user_id)
    if not user:
        print("检查完成，没有注册，帮忙注册中...")
        nickname = (await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']
        xme_user = User(database, user_id, nickname)
        xme_user.save()
        print("注册完成。")
        await send_msg(session, "执行时我帮你注册了一个新账号哦 owo")
    else:
        xme_user = user
    print(f"检查完成，已注册")
    # print(xme_user)
    return xme_user