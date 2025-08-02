from starlette.requests import Request
from starlette.responses import JSONResponse

from config.log_config import app_logger


class TrainingException(Exception):
    """通用业务异常。

    Attributes:
        code: 系统内部错误码，前端可据此做业务判断。
        message: 友好提示信息。
        status: HTTP 状态码，默认为 400。
    """

    def __init__(self, code: int = 40000, message: str = "文件异常", status: int = 200):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)



async def training_exception_handler(request: Request, exc: TrainingException):
    """FastAPI 异常处理器：统一返回格式并记录日志。"""
    # 记录业务异常
    app_logger.warning(f"TrainingException | code={exc.code} | message={exc.message} | url={request.url}")
    
    return JSONResponse(
        status_code=exc.status,
        headers={"Access-Control-Allow-Origin": "*"},
        content={"code": exc.code, "message": exc.message, "data": None},
    )

