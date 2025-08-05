# -*- coding: utf-8 -*-
#  author: ict

import json
from typing import Dict

USER_CHAT_STATE = "CHAT_STATUS"
USER_CHAT_STATE_TTL = 2 * 24 * 3600

USER_CHAT_ID = "CHAT_ID"
USER_CHAT_ID_TTL = 3000

# 用户当前chat_id存储
USER_CURRENT_CHAT_ID = "CURRENT_CHAT_ID"


class PaperTestStateProcessor:
    """试卷测试状态处理器"""
    
    # 试卷相关缓存键前缀
    PAPER_GENERATE_KEY = "PAPER_GENERATE"
    PAPER_ANALYZE_KEY = "PAPER_ANALYZE"
    PAPER_CACHE_TTL = 24 * 3600  # 24小时过期
    
    # 新增：共享试题相关缓存键前缀
    SHARED_PAPER_KEY = "SHARED_PAPER"  # 共享试题缓存
    ACCESS_CODE_MAP_KEY = "ACCESS_CODE_MAP"  # 访问码映射
    USER_ANSWER_KEY = "USER_ANSWER"  # 用户答题缓存
    SHARED_PAPER_TTL = 7 * 24 * 3600  # 7天过期
    

    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def save_generated_paper(
            self,
            user_id: str,
            chat_id: str,
            paper_data: dict
    ) -> None:
        """
        保存生成的试卷信息到Redis
        
        Args:
            user_id: 用户ID
            chat_id: 聊天会话ID
            paper_data: 试卷数据
        """
        cache_key = f"{self.PAPER_GENERATE_KEY}:{user_id}:{chat_id}"
        paper_data_str = json.dumps(paper_data, ensure_ascii=False)
        self.redis_client.set(cache_key, paper_data_str, ex=self.PAPER_CACHE_TTL)
    
    def get_generated_paper(
            self,
            user_id: str,
            chat_id: str
    ) -> Dict:
        """
        从Redis获取生成的试卷信息
        
        Args:
            user_id: 用户ID
            chat_id: 聊天会话ID
            
        Returns:
            试卷数据，如果不存在则返回None
        """
        cache_key = f"{self.PAPER_GENERATE_KEY}:{user_id}:{chat_id}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            # 刷新过期时间
            self.redis_client.expire(cache_key, self.PAPER_CACHE_TTL)
            return json.loads(cached_data)
        return None
    
    # 新增：共享试题相关方法
    def save_shared_paper(self, paper_id: str, paper_data: dict) -> None:
        """
        保存共享试题到Redis
        
        Args:
            paper_id: 试题ID
            paper_data: 试题数据
        """
        cache_key = f"{self.SHARED_PAPER_KEY}:{paper_id}"
        paper_data_str = json.dumps(paper_data, ensure_ascii=False)
        self.redis_client.set(cache_key, paper_data_str, ex=self.SHARED_PAPER_TTL)
    
    def get_shared_paper(self, paper_id: str) -> Dict:
        """
        从Redis获取共享试题
        
        Args:
            paper_id: 试题ID
            
        Returns:
            试题数据，如果不存在则返回None
        """
        cache_key = f"{self.SHARED_PAPER_KEY}:{paper_id}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            # 刷新过期时间
            self.redis_client.expire(cache_key, self.SHARED_PAPER_TTL)
            return json.loads(cached_data)
        return None
    
    def save_access_code_mapping(self, access_code: str, paper_id: str) -> None:
        """
        保存访问码到试题ID的映射
        
        Args:
            access_code: 访问码
            paper_id: 试题ID
        """
        cache_key = f"{self.ACCESS_CODE_MAP_KEY}:{access_code}"
        self.redis_client.set(cache_key, paper_id, ex=self.SHARED_PAPER_TTL)
    
    def get_paper_id_by_access_code(self, access_code: str) -> str:
        """
        根据访问码获取试题ID
        
        Args:
            access_code: 访问码
            
        Returns:
            试题ID，如果不存在则返回None
        """
        cache_key = f"{self.ACCESS_CODE_MAP_KEY}:{access_code}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            # 刷新过期时间
            self.redis_client.expire(cache_key, self.SHARED_PAPER_TTL)
            return cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data
        return None
    
    def save_user_answer(self, paper_id: str, user_id: str, answer_data: dict) -> None:
        """
        保存用户答题记录到Redis
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            answer_data: 答题数据
        """
        cache_key = f"{self.USER_ANSWER_KEY}:{paper_id}:{user_id}"
        answer_data_str = json.dumps(answer_data, ensure_ascii=False)
        self.redis_client.set(cache_key, answer_data_str, ex=self.SHARED_PAPER_TTL)
    
    def get_user_answer(self, paper_id: str, user_id: str) -> Dict:
        """
        从Redis获取用户答题记录
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            
        Returns:
            答题数据，如果不存在则返回None
        """
        cache_key = f"{self.USER_ANSWER_KEY}:{paper_id}:{user_id}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            # 刷新过期时间
            self.redis_client.expire(cache_key, self.SHARED_PAPER_TTL)
            return json.loads(cached_data)
        return None
    
    def delete_shared_paper(self, paper_id: str) -> None:
        """
        删除共享试题缓存
        
        Args:
            paper_id: 试题ID
        """
        cache_key = f"{self.SHARED_PAPER_KEY}:{paper_id}"
        self.redis_client.delete(cache_key)
    
    def delete_access_code_mapping(self, access_code: str) -> None:
        """
        删除访问码映射
        
        Args:
            access_code: 访问码
        """
        cache_key = f"{self.ACCESS_CODE_MAP_KEY}:{access_code}"
        self.redis_client.delete(cache_key)
    

