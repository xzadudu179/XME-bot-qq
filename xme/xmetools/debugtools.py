from config import DEBUG
from nonebot import logger

def debug_msg(*args, **kwargs):
    logger.debug(" ".join([str(a) for a in list(args)]), **kwargs)

def debugging():
    return DEBUG
