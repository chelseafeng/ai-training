# -*- coding: utf-8 -*-
"""访问码生成工具"""

import uuid
import random
import string
from typing import Optional
from datetime import datetime


def generate_paper_id() -> str:
    """
    生成试题ID
    
    Returns:
        试题ID，格式：PAPER_YYYYMMDD_XXXXXXXX
    """
    today = datetime.now().strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:8].upper()
    return f"PAPER_{today}_{random_part}"


def generate_access_code(length: int = 6) -> str:
    """
    生成访问码
    
    Args:
        length: 访问码长度，默认6位
        
    Returns:
        访问码，格式：大写字母和数字组合
    """
    # 排除容易混淆的字符：0, O, I, 1
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(random.choice(chars) for _ in range(length))


def generate_unique_access_code(
    check_exists_func: Optional[callable] = None,
    max_attempts: int = 10
) -> str:
    """
    生成唯一访问码
    
    Args:
        check_exists_func: 检查访问码是否存在的函数
        max_attempts: 最大尝试次数
        
    Returns:
        唯一的访问码
        
    Raises:
        ValueError: 如果超过最大尝试次数仍无法生成唯一访问码
    """
    for attempt in range(max_attempts):
        access_code = generate_access_code()
        
        # 如果没有提供检查函数，直接返回
        if check_exists_func is None:
            return access_code
        
        # 检查访问码是否已存在
        if not check_exists_func(access_code):
            return access_code
    
    raise ValueError(f"无法在{max_attempts}次尝试内生成唯一访问码")


def validate_access_code(access_code: str) -> bool:
    """
    验证访问码格式
    
    Args:
        access_code: 访问码
        
    Returns:
        是否为有效的访问码格式
    """
    if not access_code:
        return False
    
    # 长度检查
    if len(access_code) < 4 or len(access_code) > 10:
        return False
    
    # 字符检查：只允许大写字母和数字
    allowed_chars = set(string.ascii_uppercase + string.digits)
    return all(c in allowed_chars for c in access_code)


def format_access_code_url(access_code: str, base_url: str = "") -> str:
    """
    格式化访问码URL
    
    Args:
        access_code: 访问码
        base_url: 基础URL
        
    Returns:
        完整的访问URL
    """
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    return f"{base_url}/paper/access/{access_code}" 