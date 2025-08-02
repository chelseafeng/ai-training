# -*- coding: utf-8 -*-

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

DataT = TypeVar('DataT')


class MessageSchema(BaseModel):
    type: str = Field(default='InvalidRequest')
    message: str = Field(default='请求参数错误或者不完整')


error_message = MessageSchema()


class ApiErrorResponse(BaseModel):
    """
        统一返回错误类型
    """

    code: int = Field(default=400)
    status: str = Field(default='')
    error: Optional[MessageSchema] = Field(default=error_message)
    message: str = Field(default='系统异常')


class ApiSuccessResponse(BaseModel, Generic[DataT]):
    """
        统一返回成功类型
    """
    data: Optional[DataT] = None
    code: int = Field(default=200)
    status: str = Field(default='success')
    message: str = Field(default='请求成功处理')
