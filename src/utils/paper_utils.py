# -*- coding: utf-8 -*-
#  author: ict
from typing import Dict, Any, List
from schemas.paper_schemas import (
    QuestionForFrontend,
    QuestionOptionForFrontend
)


def hide_correct_answers(questions: List[Dict[str, Any]]) -> List[QuestionForFrontend]:
    """
    隐藏题目中的正确答案信息
    
    Args:
        questions: 包含完整信息的题目列表
        
    Returns:
        隐藏正确答案的题目列表
    """
    frontend_questions = []
    
    for question in questions:
        # 处理选项，移除正确答案标识和解释
        frontend_options = []
        for option in question.get('options', []):
            frontend_option = QuestionOptionForFrontend(
                id=option.get('id', ''),
                text=option.get('text', '')
            )
            frontend_options.append(frontend_option)
        
        # 创建前端题目对象
        frontend_question = QuestionForFrontend(
            question_id=question.get('question_id', ''),
            question_type=question.get('question_type', ''),
            question_text=question.get('question_text', ''),
            options=frontend_options
        )
        frontend_questions.append(frontend_question)
    
    return frontend_questions


def build_analysis_tasks_from_cache(
    cached_questions: List[Dict[str, Any]], 
    user_answers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    从缓存的题目信息和用户答案构建分析任务
    
    Args:
        cached_questions: 缓存中的完整题目信息
        user_answers: 用户答案列表（字典格式）
        
    Returns:
        分析任务列表
    """
    analysis_tasks = []
    
    # 创建题目ID到题目的映射
    question_map = {}
    for question in cached_questions:
        question_id = str(question.get('question_id', ''))
        question_map[question_id] = question
    
    # 遍历用户答案，构建分析任务
    for user_answer in user_answers:
        question_id = str(user_answer.get('question_id', ''))
        
        if question_id not in question_map:
            raise ValueError(f"题目ID {question_id} 在缓存中不存在")
        
        cached_question = question_map[question_id]
        
        # 构建分析任务，保持用户答案的原始格式（字符串或列表）
        analysis_task = {
            "question_id": question_id,
            "question_type": cached_question.get('question_type', ''),
            "question_text": cached_question.get('question_text', ''),
            "user_answer": user_answer.get('user_answer', ''),  # 保持原始格式
            "options": cached_question.get('options', [])
        }
        
        analysis_tasks.append(analysis_task)
    
    return analysis_tasks


def convert_question_type_to_chinese(question_type: str) -> str:
    """
    将题目类型转换为中文显示
    
    Args:
        question_type: 英文题目类型
        
    Returns:
        中文题目类型
    """
    type_mapping = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'true_false': '判断题',
        'fill_blank': '填空题'
    }
    
    return type_mapping.get(question_type, question_type) 