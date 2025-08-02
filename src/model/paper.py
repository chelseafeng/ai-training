# -*- coding: utf-8 -*-
"""试题数据库模型"""

from sqlalchemy import Column, String, Integer, Text, DateTime, DECIMAL
from sqlalchemy.sql import func
from config.db_config import Base


class Paper(Base):
    """试题表模型"""
    __tablename__ = 'papers'
    
    paper_id = Column(String(50), primary_key=True, comment='试题ID')
    questions = Column(Text, nullable=False, comment='试题内容(JSON字符串)')
    total_count = Column(Integer, nullable=False, comment='题目总数')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    status = Column(String(20), default='active', comment='状态')
    access_code = Column(String(50), unique=True, nullable=False, comment='访问码')
    user_id = Column(String(50), comment='创建者用户ID')
    
    def __repr__(self):
        return f"<Paper(paper_id='{self.paper_id}', access_code='{self.access_code}', total_count={self.total_count})>"


class UserAnswer(Base):
    """用户答题记录表模型"""
    __tablename__ = 'user_answers'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    paper_id = Column(String(50), nullable=False, comment='试题ID')
    user_id = Column(String(50), nullable=False, comment='用户ID')
    answers = Column(Text, comment='用户答案(JSON字符串)')
    score = Column(DECIMAL(5, 2), comment='得分')
    correct_count = Column(Integer, comment='正确题目数')
    total_count = Column(Integer, comment='总题目数')
    analysis_results = Column(Text, comment='分析结果(JSON字符串)')
    overall_feedback = Column(Text, comment='整体反馈')
    submitted_at = Column(DateTime, server_default=func.now(), comment='提交时间')
    
    def __repr__(self):
        return f"<UserAnswer(id={self.id}, paper_id='{self.paper_id}', user_id='{self.user_id}', score={self.score})>" 