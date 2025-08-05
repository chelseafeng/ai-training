# -*- coding: utf-8 -*-
#  author: ict
from datetime import datetime
from typing import Dict, Any, List
import os

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy.orm import Session

from config import log_config
from controller.dependencies import get_redis_client
from config.db_config import get_db
from service.shared_paper_service import SharedPaperService
from schemas.common_schemas import ApiSuccessResponse
from schemas.paper_schemas import (
    GeneratePaperRequest,
    GeneratePaperResponse,
    AnalyzePaperSimpleRequest,
    AnalyzePaperResponse,
    CachedPaperData,
    QuestionForGenerate,
    QuestionOptionForGenerate,
    SharedPaperRequest,
    SharedPaperResponse,
    GetPaperRequest,
    GetPaperResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    GetResultRequest,
    GetResultResponse
)
from service.analyze_paper_service import analyze_paper_answers
from service.generate_paper_service import generate_training_questions
from utils.redis_util import PaperTestStateProcessor
from utils.paper_utils import hide_correct_answers, build_analysis_tasks_from_cache
from utils.file_download_util import process_file_list
from config.app_config import STATIC_FILE_PATH


router = APIRouter(prefix="/paper", tags=["培训考试题目"])


@router.post("/generate", response_model=ApiSuccessResponse[GeneratePaperResponse])
async def generate_paper(
        request: GeneratePaperRequest,
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[GeneratePaperResponse]:
    """
    生成测试试题
    
    根据提供的文件信息列表生成培训测试题，并缓存完整结果
    
    Args:
        request: 生成试题请求参数
        redis_client: Redis客户端依赖
        
    Returns:
        生成的测试试题列表（隐藏正确答案）
    """
    try:
        # 创建试卷状态处理器
        paper_processor = PaperTestStateProcessor(redis_client)

        # 处理文件列表，确保所有文件都可用
        knowledge_dir = os.path.join(STATIC_FILE_PATH, 'knowledge')
        if request.file_list:
            # 将FileInfo对象转换为字典列表
            file_dict_list = [file_info.dict() for file_info in request.file_list]
            available_files = process_file_list(file_dict_list, knowledge_dir)
        else:
            # 如果没有提供文件列表，使用默认文档
            available_files = []

        # 调用service层生成试题
        result = generate_training_questions(
            doc_files=available_files
        )

        # 构建完整的缓存数据
        questions = result.get('questions', [])
        cache_data = CachedPaperData(
            questions=[
                QuestionForGenerate(
                    question_id=str(q.get('question_id', '')),
                    question_type=q.get('question_type', ''),
                    question_text=q.get('question_text', ''),
                    options=[
                        QuestionOptionForGenerate(
                            id=opt.get('id', ''),
                            text=opt.get('text', ''),
                            is_correct=opt.get('is_correct', False),
                            explanation=opt.get('explanation', '')
                        ) for opt in q.get('options', [])
                    ]
                ) for q in questions
            ],
            total_count=len(questions),
            user_id=request.user_id,
            chat_id=request.chat_id,
            created_at=datetime.now().isoformat()
        )

        # 保存完整数据到缓存
        paper_processor.save_generated_paper(request.user_id, request.chat_id, cache_data.dict())

        # 隐藏正确答案用于前端返回
        frontend_questions = hide_correct_answers(questions)

        response_data = GeneratePaperResponse(
            questions=frontend_questions,
            total_count=len(frontend_questions),
            user_id=request.user_id,
            chat_id=request.chat_id
        )

        log_config.app_logger.info(f"成功生成 {len(questions)} 道测试题，用户: {request.user_id}, 会话: {request.chat_id}")

        return ApiSuccessResponse(
            data=response_data,
            message="测试试题生成成功"
        )

    except ValueError as e:
        log_config.app_logger.error(f"生成试题参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_config.app_logger.error(f"生成试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成试题时发生内部错误")


@router.post("/analyze", response_model=ApiSuccessResponse[AnalyzePaperResponse])
async def analyze_paper_simple(
        request: AnalyzePaperSimpleRequest,
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[AnalyzePaperResponse]:
    """
    分析测试试题（简化版本）
    
    用户只需传递答案列表，系统从缓存中获取完整题目信息进行分析
    
    Args:
        request: 简化的分析试题请求参数
        redis_client: Redis客户端依赖
        
    Returns:
        试题分析结果
    """
    try:
        # 创建试卷状态处理器
        paper_processor = PaperTestStateProcessor(redis_client)

        # 从缓存中获取生成的题目信息
        cached_generate_result = paper_processor.get_generated_paper(request.user_id, request.chat_id)
        if not cached_generate_result:
            raise ValueError(f"未找到用户 {request.user_id} 会话 {request.chat_id} 的题目缓存，请先生成试题")

        cached_questions = cached_generate_result.get('questions', [])
        if not cached_questions:
            raise ValueError("缓存中的题目信息为空")

        # 构建分析任务
        analysis_tasks = build_analysis_tasks_from_cache(cached_questions, request.answers)

        log_config.app_logger.info(f"从缓存构建分析输入，共 {len(analysis_tasks)}个题目")

        # 调用service层分析试题（只调用一次大模型服务）
        result = analyze_paper_answers(analysis_tasks=analysis_tasks)

        # 构建响应数据
        analysis_results = result.get('analysis_results', [])
        total_score = result.get('total_score', 0.0)
        correct_count = result.get('correct_count', 0)
        total_count = result.get('total_count', len(analysis_tasks))
        overall_feedback = result.get('overall_feedback', '')

        response_data = AnalyzePaperResponse(
            analysis_results=analysis_results,
            total_score=total_score,
            correct_count=correct_count,
            total_count=total_count,
            overall_feedback=overall_feedback,
            user_id=request.user_id,
            chat_id=request.chat_id
        )

        return ApiSuccessResponse(
            data=response_data,
            message="试题分析完成"
        )

    except ValueError as e:
        log_config.app_logger.error(f"分析试题参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_config.app_logger.error(f"分析试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分析试题时发生内部错误")


# 新增：共享试题相关接口
@router.post("/shared/generate", response_model=ApiSuccessResponse[SharedPaperResponse])
async def generate_shared_paper(
        request: SharedPaperRequest,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[SharedPaperResponse]:
    """
    生成共享试题
    
    生成可被多个用户访问的试题，返回试题ID和访问码
    
    Args:
        request: 生成共享试题请求参数
        db: 数据库会话依赖
        redis_client: Redis客户端依赖
        
    Returns:
        生成的共享试题信息，包含访问码和访问链接
    """
    try:
        shared_paper_service = SharedPaperService(db, redis_client)
        
        # 将FileInfo对象转换为字典列表
        file_list = None
        if request.file_list:
            file_list = [file_info.dict() for file_info in request.file_list]
        
        result = shared_paper_service.generate_shared_paper(
            user_id=request.user_id,
            file_list=file_list
        )
        
        response_data = SharedPaperResponse(
            paper_id=result['paper_id'],
            access_code=result['access_code'],
            access_url=result['access_url'],
            total_count=result['total_count'],
            created_at=result['created_at']
        )
        
        log_config.app_logger.info(f"成功生成共享试题: {result['paper_id']}, 访问码: {result['access_code']}")
        
        return ApiSuccessResponse(
            data=response_data,
            message="共享试题生成成功"
        )
        
    except ValueError as e:
        log_config.app_logger.error(f"生成共享试题参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_config.app_logger.error(f"生成共享试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成共享试题时发生内部错误")


@router.get("/shared/{paper_id}", response_model=ApiSuccessResponse[GetPaperResponse])
async def get_shared_paper_by_id(
        paper_id: str,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[GetPaperResponse]:
    """
    根据试题ID获取共享试题
    
    Args:
        paper_id: 试题ID
        db: 数据库会话依赖
        redis_client: Redis客户端依赖
        
    Returns:
        试题信息（隐藏答案）
    """
    try:
        shared_paper_service = SharedPaperService(db, redis_client)
        result = shared_paper_service.get_paper_by_id(paper_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="试题不存在或已失效")
        
        response_data = GetPaperResponse(
            paper_id=result['paper_id'],
            access_code=result['access_code'],
            questions=result['questions'],
            total_count=result['total_count'],
            created_at=result['created_at'],
            documents=result.get('documents', []),
            document_count=result.get('document_count', 0)
        )
        
        return ApiSuccessResponse(
            data=response_data,
            message="获取试题成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_config.app_logger.error(f"获取共享试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取试题时发生内部错误")


@router.get("/access/{access_code}", response_model=ApiSuccessResponse[GetPaperResponse])
async def get_shared_paper_by_access_code(
        access_code: str,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[GetPaperResponse]:
    """
    根据访问码获取共享试题
    
    Args:
        access_code: 访问码
        db: 数据库会话依赖
        redis_client: Redis客户端依赖
        
    Returns:
        试题信息（隐藏答案）
    """
    try:
        shared_paper_service = SharedPaperService(db, redis_client)
        result = shared_paper_service.get_paper_by_access_code(access_code)
        
        if not result:
            raise HTTPException(status_code=404, detail="试题不存在或访问码无效")
        
        response_data = GetPaperResponse(
            paper_id=result['paper_id'],
            access_code=result['access_code'],
            questions=result['questions'],
            total_count=result['total_count'],
            created_at=result['created_at'],
            documents=result.get('documents', []),
            document_count=result.get('document_count', 0)
        )
        
        return ApiSuccessResponse(
            data=response_data,
            message="获取试题成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_config.app_logger.error(f"通过访问码获取共享试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取试题时发生内部错误")


@router.post("/shared/{paper_id}/submit", response_model=ApiSuccessResponse[SubmitAnswerResponse])
async def submit_shared_paper_answers(
        paper_id: str,
        request: SubmitAnswerRequest,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[SubmitAnswerResponse]:
    """
    提交共享试题答案
    
    Args:
        paper_id: 试题ID
        request: 提交答案请求参数
        db: 数据库会话依赖
        redis_client: Redis客户端依赖
        
    Returns:
        答题分析结果
    """
    try:
        shared_paper_service = SharedPaperService(db, redis_client)
        
        # 将UserAnswer对象转换为字典列表
        answers = [answer.dict() for answer in request.answers]
        
        result = shared_paper_service.submit_answers(
            paper_id=paper_id,
            user_id=request.user_id,
            answers=answers
        )
        
        response_data = SubmitAnswerResponse(
            paper_id=result['paper_id'],
            user_id=result['user_id'],
            submitted_at=result['submitted_at'],
            message="答案提交成功，请查看答题结果"
        )
        
        log_config.app_logger.info(f"用户 {request.user_id} 成功提交试题 {paper_id} 答案，等待查看结果")
        
        return ApiSuccessResponse(
            data=response_data,
            message="答案提交成功"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        log_config.app_logger.error(f"提交答案参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_config.app_logger.error(f"提交答案失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提交答案时发生内部错误")


@router.get("/shared/{paper_id}/result/{user_id}", response_model=ApiSuccessResponse[GetResultResponse])
async def get_shared_paper_result(
        paper_id: str,
        user_id: str,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client)
) -> ApiSuccessResponse[GetResultResponse]:
    """
    获取用户答题结果
    
    Args:
        paper_id: 试题ID
        user_id: 用户ID
        db: 数据库会话依赖
        redis_client: Redis客户端依赖
        
    Returns:
        用户答题结果
    """
    try:
        shared_paper_service = SharedPaperService(db, redis_client)
        result = shared_paper_service.get_user_result(paper_id, user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="未找到该用户的答题记录")
        
        response_data = GetResultResponse(
            paper_id=result['paper_id'],
            user_id=result['user_id'],
            analysis_results=result['analysis_results'],
            total_score=result.get('total_score', result.get('score', 0.0)),
            correct_count=result['correct_count'],
            total_count=result['total_count'],
            overall_feedback=result['overall_feedback'],
            submitted_at=result['submitted_at'],
            documents=result.get('documents', []),
            document_count=result.get('document_count', 0)
        )
        
        return ApiSuccessResponse(
            data=response_data,
            message="获取答题结果成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_config.app_logger.error(f"获取答题结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取答题结果时发生内部错误")




