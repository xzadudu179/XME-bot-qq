# 注册账号 或签到
from xme.xmetools import date_tools
from .xme_config import *
import sqlite3
from nonebot import log
import random
import config
from nonebot import on_command, CommandSession

register_alias = ["reg", "r"]
@on_command('register', aliases=register_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
async def _(session: CommandSession):
    user_id = session.event.user_id
    nickname = (await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']
    xme_user_db_init()
    conn = sqlite3.connect(XME_DB_PATH)
    try:
        message = "签到成功~"
        cursor = conn.cursor()
        coins = random.randint(5, 100)
        # 如果数据库里没有该用户信息 则先注册后签到
        cursor.execute("SELECT last_reg_days FROM users WHERE id = ?", (user_id,))
        rows = cursor.fetchall()
        message = f"[CQ:at,qq={user_id}] 签到成功~ 你获得了 {coins} 枚虚拟星币！"
        if len(rows) < 1:
            # 注册
            # 顺便签到
            cursor.execute('''
                INSERT INTO users (id, name, last_reg_days, coins)
                VALUES (?, ?, ?, ?)
            ''', (user_id, nickname, date_tools.curr_days(), coins))
            message += "\n顺便帮你注册了账号 ovo"
        else:
            # 有用户
            last_reg_days = rows[0][0]
            if last_reg_days >= date_tools.curr_days():
                message = f"[CQ:at,qq={user_id}] 你今天已经签到过了哦 ovo"
            else:
                cursor.execute('''
                    UPDATE users
                    SET last_reg_days = ?, coins = ?
                    WHERE id = ?
                ''', (date_tools.curr_days(), coins, user_id))
        conn.commit()
        await session.send(message)
    except Exception as ex:
        log.logger.error(f"ERROR: XME 注册/签到出现问题: {ex}\n{ex.with_traceback()}")
        conn.rollback()
    finally:
        conn.close()

# 初始化用户数据库
def xme_user_db_init():
    conn = sqlite3.connect(XME_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            last_reg_days INTEGER,
            coins INTEGER
        )
    ''')