# -*- coding: utf-8 -*-
#  author: ict
from redis import Redis

from config.app_config import CONFIG

def get_redis_client():
    """
    获取 Redis 客户端实例

    Args:
        db: Redis 数据库编号，默认使用 12 号数据库
    """
    client = Redis(
        host=CONFIG['redis_host'],
        port=CONFIG['redis_port'],
        decode_responses=True,
        password=CONFIG["redis_password"],
        username=CONFIG['redis_username'],
        db=CONFIG['redis_db']
    )
    try:
        yield client
    finally:
        client.close()



