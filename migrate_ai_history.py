# -*- coding: utf-8 -*-
"""
将旧版存储在 User 数据表 ai_history 字段里的 AI 会话历史，迁移到
data/ai_historys/<用户id>/default.json（ai_helper 的上下文新存储位置）。

两种用法（二选一即可）：
    1) 手动：python migrate_ai_history.py [--clear-old]
    2) 自动：bot 启动时会自动调用 migrate()（见 bot.py），跑完你想删掉这个脚本即可。

迁移是幂等的：旧 ai_history 为空、或目标文件已存在（说明已迁移/在用新会话）的
用户会被跳过，不会覆盖新数据。--clear-old 会顺带把旧 ai_history 字段清空为 "[]"。
"""
import argparse
import json
from pathlib import Path

# 与 xme/plugins/commands/ai_helper/history.py 保持一致
HISTORY_ROOT = Path("./data/ai_historys")
DEFAULT_SESSION = "default"


def _target_path(user_id) -> Path:
    return HISTORY_ROOT / str(user_id) / f"{DEFAULT_SESSION}.json"


def migrate(clear_old=False) -> dict:
    """执行迁移，返回统计信息。"""
    from xme.plugins.commands.xme_user.classes.user import User

    stats = {"users": 0, "migrated": 0, "skipped": 0, "cleared": 0}
    try:
        users = User.get_users()
    except Exception as ex:
        stats["error"] = str(ex)
        return stats

    stats["users"] = len(users)
    for u in users:
        uid = u.get("user_id")
        ai = u.get("ai_history") or []
        if not uid:
            continue
        target = _target_path(uid)
        if not ai:
            stats["skipped"] += 1
            continue
        if target.exists():
            # 已迁移过 / 已在使用新的会话存储，跳过避免覆盖
            stats["skipped"] += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(ai, ensure_ascii=False, indent=2), encoding="utf-8")
        stats["migrated"] += 1
        if clear_old:
            from xme.xmetools.dbtools import DATABASE
            DATABASE.exec_query(
                "UPDATE User SET ai_history = ? WHERE user_id = ?",
                params=("[]", uid),
            )
            stats["cleared"] += 1
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="迁移旧版 ai_history 到 data/ai_historys")
    parser.add_argument("--clear-old", action="store_true",
                        help="迁移后把旧 ai_history 字段清空为 []")
    args = parser.parse_args()
    print("开始迁移旧的 ai_history ...")
    result = migrate(clear_old=args.clear_old)
    print("迁移完成：", result)
