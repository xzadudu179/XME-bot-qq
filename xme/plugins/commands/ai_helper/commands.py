
def clear_history(user_id, history, **kwargs) -> str:
    user_id = str(user_id)
    u_history = history.get(user_id, None)
    if u_history is None:
        return "历史记录清除失败：没有历史记录"
    del history[user_id]
    return "历史记录清除成功"