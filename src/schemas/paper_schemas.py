# -*- coding: utf-8 -*-
#  author: ict
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """文件信息模型"""
    file_bucket_name: str = Field(None, description="存储桶中的文件名")
    file_id: str = Field(None, description="文件唯一标识符")
    file_location: str = Field(..., description="文件下载URL")
    file_name: str = Field(..., description="人类可读的文件名")
    knowledge_id: str = Field(None, description="知识库ID")
    knowledge_name: str = Field(None, description="知识库名称")


class GeneratePaperRequest(BaseModel):
    """生成测试试题请求模型"""
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")
    file_list: Optional[List[FileInfo]] = Field(None, description="文件信息列表")


class QuestionOptionForGenerate(BaseModel):
    """题目选项模型（用于生成，包含完整信息）"""
    id: str = Field(..., description="选项ID")
    text: str = Field(..., description="选项文本")
    is_correct: bool = Field(..., description="是否为正确答案")
    explanation: Optional[str] = Field(None, description="选项解释")


class QuestionOptionForFrontend(BaseModel):
    """题目选项模型（用于前端，隐藏正确答案）"""
    id: str = Field(..., description="选项ID")
    text: str = Field(..., description="选项文本")


class QuestionForGenerate(BaseModel):
    """题目模型（用于生成，包含完整信息）"""
    question_id: str | int = Field(..., description="题目ID")
    question_type: str = Field(..., description="题目类型")
    question_text: str = Field(..., description="题目文本")
    options: List[QuestionOptionForGenerate] = Field(..., description="选项列表")


class QuestionForFrontend(BaseModel):
    """题目模型（用于前端，隐藏正确答案）"""
    question_id: str | int = Field(..., description="题目ID")
    question_type: str = Field(..., description="题目类型")
    question_text: str = Field(..., description="题目文本")
    options: List[QuestionOptionForFrontend] = Field(..., description="选项列表")


class GeneratePaperResponse(BaseModel):
    """生成测试试题响应模型（返回前端，隐藏正确答案）"""
    questions: List[QuestionForFrontend] = Field(..., description="生成的题目列表")
    total_count: int = Field(..., description="题目总数")
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")


class UserAnswer(BaseModel):
    """用户答案模型"""
    question_id: str = Field(..., description="题目ID")
    user_answer: str | list = Field(..., description="用户答案（单选题为字符串，多选题为列表）")


class AnalyzePaperSimpleRequest(BaseModel):
    """分析测试试题简化请求模型（新版本）"""
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")
    answers: List[UserAnswer] = Field(..., description="用户答案列表")


class AnalysisTask(BaseModel):
    """分析任务模型"""
    question_id: str = Field(..., description="题目ID")
    question_type: str = Field(..., description="题目类型")
    question_text: str = Field(..., description="题目文本")
    user_answer: str | list = Field(..., description="用户答案（单选题为字符串，多选题为列表）")
    options: List[QuestionOptionForGenerate] = Field(..., description="选项列表")


class AnalyzePaperRequest(BaseModel):
    """分析测试试题请求模型（原版本，保持向后兼容）"""
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")
    analysis_tasks: List[AnalysisTask] = Field(..., description="分析任务列表")



class QuestionAnalysis(BaseModel):
    """题目分析结果模型"""
    question_id: str = Field(..., description="题目ID")
    question_type: str = Field(..., description="题目类型")
    question_text: str = Field(..., description="题目文本")
    user_answer: str | list = Field(..., description="用户答案（单选题为字符串，多选题为列表）")
    is_correct: bool = Field(..., description="答案是否正确")
    score: float = Field(..., description="得分")
    correct_answer: str | list = Field(..., description="正确答案（单选题为字符串，多选题为列表）")
    explanation: str = Field(..., description="详细解释")


class AnalyzePaperResponse(BaseModel):
    """分析测试试题响应模型"""
    analysis_results: List[QuestionAnalysis] = Field(..., description="分析结果列表")
    total_score: float = Field(..., description="总分")
    correct_count: int = Field(..., description="正确题目数")
    total_count: int = Field(..., description="总题目数")
    overall_feedback: str = Field(..., description="整体评价")
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")


# 用于缓存的完整数据模型
class CachedPaperData(BaseModel):
    """缓存的试卷数据模型（包含完整信息）"""
    questions: List[QuestionForGenerate] = Field(..., description="完整的题目列表")
    total_count: int = Field(..., description="题目总数")
    user_id: str = Field(..., description="用户ID")
    chat_id: str = Field(..., description="聊天会话ID")
    created_at: str = Field(..., description="创建时间")


# 新增：试题共享相关的schemas
class SharedPaperRequest(BaseModel):
    """生成共享试题请求模型"""
    user_id: Optional[str] = Field(None, description="创建者ID")
    file_list: Optional[List[FileInfo]] = Field(None, description="文件信息列表")


class SharedPaperResponse(BaseModel):
    """生成共享试题响应模型"""
    paper_id: str = Field(..., description="试题ID")
    access_code: str = Field(..., description="访问码")
    access_url: str = Field(..., description="访问链接")
    total_count: int = Field(..., description="题目总数")
    created_at: str = Field(..., description="创建时间")


class GetPaperRequest(BaseModel):
    """获取试题请求模型"""
    paper_id: Optional[str] = Field(None, description="试题ID")
    access_code: Optional[str] = Field(None, description="访问码")


class GetPaperResponse(BaseModel):
    """获取试题响应模型"""
    paper_id: str = Field(..., description="试题ID")
    access_code: str = Field(..., description="访问码")
    questions: List[QuestionForFrontend] = Field(..., description="题目列表（隐藏答案）")
    total_count: int = Field(..., description="题目总数")
    created_at: str = Field(..., description="创建时间")


class SubmitAnswerRequest(BaseModel):
    """提交答案请求模型"""
    user_id: str = Field(..., description="用户ID")
    answers: List[UserAnswer] = Field(..., description="用户答案列表")


class SubmitAnswerResponse(BaseModel):
    """提交答案响应模型"""
    paper_id: str = Field(..., description="试题ID")
    user_id: str = Field(..., description="用户ID")
    submitted_at: str = Field(..., description="提交时间")
    message: str = Field(..., description="提交结果消息")


class GetResultRequest(BaseModel):
    """获取答题结果请求模型"""
    paper_id: str = Field(..., description="试题ID")
    user_id: str = Field(..., description="用户ID")


class GetResultResponse(BaseModel):
    """获取答题结果响应模型"""
    paper_id: str = Field(..., description="试题ID")
    user_id: str = Field(..., description="用户ID")
    analysis_results: List[QuestionAnalysis] = Field(..., description="分析结果列表")
    total_score: float = Field(..., description="总分")
    correct_count: int = Field(..., description="正确题目数")
    total_count: int = Field(..., description="总题目数")
    overall_feedback: str = Field(..., description="整体评价")
    submitted_at: str = Field(..., description="提交时间") 