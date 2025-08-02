import http

from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException

from config.log_config import app_logger


async def general_exception_handler(request: Request, exc: Exception):
    # 如果是 HTTPException，提取它的 status_code 和 detail
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    else:
        # 普通异常，默认返回 500
        status_code = http.HTTPStatus.INTERNAL_SERVER_ERROR
        detail = str(exc)
    app_logger.info(f"通用系统异常：{detail}")
    return JSONResponse(
        status_code=status_code,  # 使用动态状态码
        headers={"Access-Control-Allow-Origin": "*"},
        content={
            "url": str(request.url),
            "error": "系统出现异常！"
        }
    )