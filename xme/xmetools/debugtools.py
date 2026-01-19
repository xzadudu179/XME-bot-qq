from config import DEBUG
from nonebot import logger

def debug_msg(*args, **kwargs):
    logger.debug(" ".join([str(l) for l in list(args)]), **kwargs)

def debugging():
    return DEBUG
