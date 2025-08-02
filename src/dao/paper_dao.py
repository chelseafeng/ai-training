# -*- coding: utf-8 -*-
"""试题数据访问对象"""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from model.paper import Paper, UserAnswer
from config.log_config import app_logger


class PaperDao:
    """试题数据访问对象"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_paper(self, paper_data: Dict[str, Any]) -> Paper:
        """
        创建新试题
        
        Args:
            paper_data: 试题数据字典
            
        Returns:
            创建的试题对象
        """
        try:
            paper = Paper(
                paper_id=paper_data['paper_id'],
                questions=json.dumps(paper_data['questions'], ensure_ascii=False),
                total_count=paper_data['total_count'],
                access_code=paper_data['access_code'],
                user_id=paper_data.get('user_id'),
                status=paper_data.get('status', 'active')
            )
            
            self.db.add(paper)
            self.db.commit()
            self.db.refresh(paper)
            
            app_logger.info(f"成功创建试题: {paper.paper_id}")
            return paper
            
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"创建试题失败: {str(e)}")
            raise
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        根据试题ID获取试题
        
        Args:
            paper_id: 试题ID
            
        Returns:
            试题对象，如果不存在则返回None
        """
        return self.db.query(Paper).filter(Paper.paper_id == paper_id).first()
    
    def get_paper_by_access_code(self, access_code: str) -> Optional[Paper]:
        """
        根据访问码获取试题
        
        Args:
            access_code: 访问码
            
        Returns:
            试题对象，如果不存在则返回None
        """
        return self.db.query(Paper).filter(Paper.access_code == access_code).first()
    
    def get_paper_questions(self, paper_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取试题的题目列表
        
        Args:
            paper_id: 试题ID
            
        Returns:
            题目列表，如果不存在则返回None
        """
        paper = self.get_paper_by_id(paper_id)
        if paper and paper.questions:
            try:
                return json.loads(paper.questions)
            except json.JSONDecodeError as e:
                app_logger.error(f"解析试题内容失败: {str(e)}")
                return None
        return None
    
    def update_paper_status(self, paper_id: str, status: str) -> bool:
        """
        更新试题状态
        
        Args:
            paper_id: 试题ID
            status: 新状态
            
        Returns:
            是否更新成功
        """
        try:
            paper = self.get_paper_by_id(paper_id)
            if paper:
                paper.status = status
                self.db.commit()
                app_logger.info(f"成功更新试题状态: {paper_id} -> {status}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"更新试题状态失败: {str(e)}")
            return False
    
    def delete_paper(self, paper_id: str) -> bool:
        """
        删除试题（同时删除相关答题记录）
        
        Args:
            paper_id: 试题ID
            
        Returns:
            是否删除成功
        """
        try:
            # 先删除相关答题记录
            self.db.query(UserAnswer).filter(UserAnswer.paper_id == paper_id).delete()
            
            # 再删除试题
            paper = self.get_paper_by_id(paper_id)
            if paper:
                self.db.delete(paper)
                self.db.commit()
                app_logger.info(f"成功删除试题: {paper_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"删除试题失败: {str(e)}")
            return False


class UserAnswerDao:
    """用户答题记录数据访问对象"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user_answer(self, answer_data: Dict[str, Any]) -> UserAnswer:
        """
        创建用户答题记录
        
        Args:
            answer_data: 答题数据字典
            
        Returns:
            创建的答题记录对象
        """
        try:
            user_answer = UserAnswer(
                paper_id=answer_data['paper_id'],
                user_id=answer_data['user_id'],
                answers=json.dumps(answer_data['answers'], ensure_ascii=False) if answer_data.get('answers') else None,
                score=answer_data.get('score'),
                correct_count=answer_data.get('correct_count'),
                total_count=answer_data.get('total_count'),
                analysis_results=json.dumps(answer_data['analysis_results'], ensure_ascii=False) if answer_data.get('analysis_results') else None,
                overall_feedback=answer_data.get('overall_feedback')
            )
            
            self.db.add(user_answer)
            self.db.commit()
            self.db.refresh(user_answer)
            
            app_logger.info(f"成功创建答题记录: 用户{answer_data['user_id']}, 试题{answer_data['paper_id']}")
            return user_answer
            
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"创建答题记录失败: {str(e)}")
            raise
    
    def get_user_answer(self, paper_id: str, user_id: str) -> Optional[UserAnswer]:
        """
        获取用户答题记录
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            
        Returns:
            答题记录对象，如果不存在则返回None
        """
        return self.db.query(UserAnswer).filter(
            and_(UserAnswer.paper_id == paper_id, UserAnswer.user_id == user_id)
        ).first()
    
    def update_user_answer(self, paper_id: str, user_id: str, answer_data: Dict[str, Any]) -> bool:
        """
        更新用户答题记录
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            answer_data: 更新的答题数据
            
        Returns:
            是否更新成功
        """
        try:
            user_answer = self.get_user_answer(paper_id, user_id)
            if user_answer:
                if 'answers' in answer_data:
                    user_answer.answers = json.dumps(answer_data['answers'], ensure_ascii=False)
                if 'score' in answer_data:
                    user_answer.score = answer_data['score']
                if 'correct_count' in answer_data:
                    user_answer.correct_count = answer_data['correct_count']
                if 'total_count' in answer_data:
                    user_answer.total_count = answer_data['total_count']
                if 'analysis_results' in answer_data:
                    user_answer.analysis_results = json.dumps(answer_data['analysis_results'], ensure_ascii=False)
                if 'overall_feedback' in answer_data:
                    user_answer.overall_feedback = answer_data['overall_feedback']
                
                self.db.commit()
                app_logger.info(f"成功更新答题记录: 用户{user_id}, 试题{paper_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"更新答题记录失败: {str(e)}")
            return False
    
    def get_paper_all_answers(self, paper_id: str) -> List[UserAnswer]:
        """
        获取试题的所有答题记录
        
        Args:
            paper_id: 试题ID
            
        Returns:
            答题记录列表
        """
        return self.db.query(UserAnswer).filter(UserAnswer.paper_id == paper_id).all()
    
    def delete_user_answer(self, paper_id: str, user_id: str) -> bool:
        """
        删除用户答题记录
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            user_answer = self.get_user_answer(paper_id, user_id)
            if user_answer:
                self.db.delete(user_answer)
                self.db.commit()
                app_logger.info(f"成功删除答题记录: 用户{user_id}, 试题{paper_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"删除答题记录失败: {str(e)}")
            return False 