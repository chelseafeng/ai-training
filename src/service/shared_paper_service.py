# -*- coding: utf-8 -*-
"""共享试题服务层"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.log_config import app_logger
from dao.paper_dao import PaperDao, UserAnswerDao
from service.generate_paper_service import generate_training_questions
from service.analyze_paper_service import analyze_paper_answers
from utils.access_code_util import generate_paper_id, generate_unique_access_code, format_access_code_url
from utils.redis_util import PaperTestStateProcessor
from utils.paper_utils import hide_correct_answers, build_analysis_tasks_from_cache
from utils.file_download_util import process_file_list
from config.app_config import STATIC_FILE_PATH
import os


class SharedPaperService:
    """共享试题服务类"""
    
    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis_client = redis_client
        self.paper_dao = PaperDao(db_session)
        self.user_answer_dao = UserAnswerDao(db_session)
        self.paper_processor = PaperTestStateProcessor(redis_client)
    
    def generate_shared_paper(
        self,
        user_id: Optional[str] = None,
        file_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        生成共享试题
        
        Args:
            created_by: 创建者ID
            file_list: 文件信息列表
            
        Returns:
            生成的共享试题信息
        """
        try:
            # 生成试题ID和访问码
            paper_id = generate_paper_id()
            
            # 检查访问码是否已存在的函数
            def check_access_code_exists(code: str) -> bool:
                return self.paper_dao.get_paper_by_access_code(code) is not None
            
            access_code = generate_unique_access_code(check_access_code_exists)
            
            # 处理文件列表，确保所有文件都可用
            knowledge_dir = os.path.join(STATIC_FILE_PATH, 'knowledge')
            if file_list:
                available_files = process_file_list(file_list, knowledge_dir)
            else:
                available_files = []
            
            # 调用service层生成试题
            result = generate_training_questions(doc_files=available_files)
            questions = result.get('questions', [])
            
            if not questions:
                raise ValueError("生成的试题为空")
            
            # 保存试题到数据库
            paper_data = {
                'paper_id': paper_id,
                'questions': questions,
                'total_count': len(questions),
                'access_code': access_code,
                'user_id': user_id,
                'status': 'active'
            }
            
            paper = self.paper_dao.create_paper(paper_data)
            
            # 提取文档文件名列表
            documents = []
            if file_list:
                documents = [file_info.get('file_name', '') for file_info in file_list]
            
            # 保存到Redis缓存
            cache_data = {
                'paper_id': paper_id,
                'questions': questions,
                'total_count': len(questions),
                'access_code': access_code,
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'documents': documents,
                'document_count': len(documents)
            }
            
            self.paper_processor.save_shared_paper(paper_id, cache_data)
            self.paper_processor.save_access_code_mapping(access_code, paper_id)
            
            # 生成访问链接
            access_url = format_access_code_url(access_code)
            
            app_logger.info(f"成功生成共享试题: {paper_id}, 访问码: {access_code}")
            
            return {
                'paper_id': paper_id,
                'access_code': access_code,
                'access_url': access_url,
                'total_count': len(questions),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            app_logger.error(f"生成共享试题失败: {str(e)}")
            raise
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        根据试题ID获取试题
        
        Args:
            paper_id: 试题ID
            
        Returns:
            试题信息（隐藏答案），如果不存在则返回None
        """
        try:
            # 先从缓存获取
            cached_data = self.paper_processor.get_shared_paper(paper_id)
            if cached_data:
                # 隐藏正确答案
                questions = cached_data.get('questions', [])
                frontend_questions = hide_correct_answers(questions)
                
                return {
                    'paper_id': cached_data['paper_id'],
                    'access_code': cached_data['access_code'],
                    'questions': frontend_questions,
                    'total_count': len(frontend_questions),
                    'created_at': cached_data.get('created_at', ''),
                    'documents': cached_data.get('documents', []),
                    'document_count': cached_data.get('document_count', 0)
                }
            
            # 从数据库获取
            paper = self.paper_dao.get_paper_by_id(paper_id)
            if not paper or paper.status != 'active':
                return None
            
            questions = self.paper_dao.get_paper_questions(paper_id)
            if not questions:
                return None
            
            # 隐藏正确答案
            frontend_questions = hide_correct_answers(questions)
            
            # 重新缓存到Redis
            cache_data = {
                'paper_id': paper.paper_id,
                'questions': questions,
                'total_count': paper.total_count,
                'access_code': paper.access_code,
                'user_id': paper.user_id,
                'created_at': paper.created_at.isoformat() if paper.created_at else '',
                'documents': [],  # 从数据库获取的试题可能没有文档信息
                'document_count': 0
            }
            self.paper_processor.save_shared_paper(paper_id, cache_data)
            self.paper_processor.save_access_code_mapping(paper.access_code, paper_id)
            
            return {
                'paper_id': paper.paper_id,
                'access_code': paper.access_code,
                'questions': frontend_questions,
                'total_count': len(frontend_questions),
                'created_at': cache_data['created_at'],
                'documents': cache_data['documents'],
                'document_count': cache_data['document_count']
            }
            
        except Exception as e:
            app_logger.error(f"获取试题失败: {str(e)}")
            return None
    
    def get_paper_by_access_code(self, access_code: str) -> Optional[Dict[str, Any]]:
        """
        根据访问码获取试题
        
        Args:
            access_code: 访问码
            
        Returns:
            试题信息（隐藏答案），如果不存在则返回None
        """
        try:
            # 先从缓存获取试题ID
            paper_id = self.paper_processor.get_paper_id_by_access_code(access_code)
            if paper_id:
                return self.get_paper_by_id(paper_id)
            
            # 从数据库获取
            paper = self.paper_dao.get_paper_by_access_code(access_code)
            if not paper or paper.status != 'active':
                return None
            
            return self.get_paper_by_id(paper.paper_id)
            
        except Exception as e:
            app_logger.error(f"根据访问码获取试题失败: {str(e)}")
            return None
    
    def submit_answers(
        self,
        paper_id: str,
        user_id: str,
        answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        提交答案并分析
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            answers: 用户答案列表
            
        Returns:
            分析结果
        """
        try:
            # 获取完整题目信息
            cached_data = self.paper_processor.get_shared_paper(paper_id)
            if not cached_data:
                # 从数据库获取
                questions = self.paper_dao.get_paper_questions(paper_id)
                if not questions:
                    raise ValueError(f"未找到试题 {paper_id}")
            else:
                questions = cached_data.get('questions', [])
            
            if not questions:
                raise ValueError("试题内容为空")
            
            # 构建分析任务
            analysis_tasks = build_analysis_tasks_from_cache(questions, answers)
            
            app_logger.info(f"构建分析输入，共 {len(analysis_tasks)} 个题目")
            
            # 调用service层分析试题
            result = analyze_paper_answers(analysis_tasks=analysis_tasks)
            
            # 构建答题记录数据
            answer_data = {
                'paper_id': paper_id,
                'user_id': user_id,
                'answers': answers,
                'score': result.get('total_score', 0.0),
                'correct_count': result.get('correct_count', 0),
                'total_count': result.get('total_count', len(analysis_tasks)),
                'analysis_results': result.get('analysis_results', []),
                'overall_feedback': result.get('overall_feedback', '')
            }
            app_logger.info(f"构建的答题记录数据: {answer_data}")
            
            # 保存到数据库
            existing_answer = self.user_answer_dao.get_user_answer(paper_id, user_id)
            if existing_answer:
                # 更新现有记录
                self.user_answer_dao.update_user_answer(paper_id, user_id, answer_data)
            else:
                # 创建新记录
                self.user_answer_dao.create_user_answer(answer_data)
            
            # 保存到Redis缓存
            cache_answer_data = answer_data.copy()
            cache_answer_data['submitted_at'] = datetime.now().isoformat()
            app_logger.info(f"保存到缓存的答题数据: {cache_answer_data}")
            self.paper_processor.save_user_answer(paper_id, user_id, cache_answer_data)
            
            app_logger.info(f"用户 {user_id} 完成试题 {paper_id} 答题，得分: {result.get('total_score', 0)}")
            
            return_data = {
                'paper_id': paper_id,
                'user_id': user_id,
                'submitted_at': datetime.now().isoformat()
            }
            app_logger.info(f"返回的提交结果数据: {return_data}")
            return return_data
            
        except Exception as e:
            app_logger.error(f"提交答案失败: {str(e)}")
            raise
    
    def get_user_result(self, paper_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户答题结果
        
        Args:
            paper_id: 试题ID
            user_id: 用户ID
            
        Returns:
            答题结果，如果不存在则返回None
        """
        try:
            app_logger.info(f"开始获取用户答题结果: paper_id={paper_id}, user_id={user_id}")
            
            # 先从缓存获取
            cached_data = self.paper_processor.get_user_answer(paper_id, user_id)
            if cached_data:
                app_logger.info(f"从缓存获取用户答题结果: {cached_data}")
                # 获取试题的文档信息
                paper_data = self.paper_processor.get_shared_paper(paper_id)
                if paper_data:
                    cached_data['documents'] = paper_data.get('documents', [])
                    cached_data['document_count'] = paper_data.get('document_count', 0)
                return cached_data
            
            # 从数据库获取
            app_logger.info(f"缓存中未找到，从数据库获取答题记录")
            user_answer = self.user_answer_dao.get_user_answer(paper_id, user_id)
            if not user_answer:
                app_logger.warning(f"数据库中未找到答题记录: paper_id={paper_id}, user_id={user_id}")
                return None
            
            app_logger.info(f"从数据库获取到答题记录: {user_answer}")
            
            # 解析JSON数据
            analysis_results = []
            if user_answer.analysis_results:
                try:
                    analysis_results = json.loads(user_answer.analysis_results)
                    app_logger.info(f"成功解析分析结果，共 {len(analysis_results)} 条")
                except json.JSONDecodeError as e:
                    app_logger.error(f"解析分析结果失败: {str(e)}")
                    pass
            
            result_data = {
                'paper_id': user_answer.paper_id,
                'user_id': user_answer.user_id,
                'analysis_results': analysis_results,
                'total_score': float(user_answer.score) if user_answer.score else 0.0,
                'correct_count': user_answer.correct_count or 0,
                'total_count': user_answer.total_count or 0,
                'overall_feedback': user_answer.overall_feedback or '',
                'submitted_at': user_answer.submitted_at.isoformat() if user_answer.submitted_at else ''
            }
            
            # 获取试题的文档信息
            paper_data = self.paper_processor.get_shared_paper(paper_id)
            if paper_data:
                result_data['documents'] = paper_data.get('documents', [])
                result_data['document_count'] = paper_data.get('document_count', 0)
            else:
                result_data['documents'] = []
                result_data['document_count'] = 0
            
            # 重新缓存到Redis
            self.paper_processor.save_user_answer(paper_id, user_id, result_data)
            
            return result_data
            
        except Exception as e:
            app_logger.error(f"获取用户答题结果失败: {str(e)}")
            import traceback
            app_logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None 