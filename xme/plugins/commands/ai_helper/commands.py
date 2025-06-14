
def clear_history(user, **kwargs) -> str:
    u_history = user.ai_history
    if not u_history:
        return "历史记录清除失败：没有历史记录"
    user.ai_history = []
    return "历史记录清除成功"