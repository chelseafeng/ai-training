from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from config.log_config import app_logger


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 打印原始错误信息
    app_logger.info(f"Validation Error:  {exc},{request.headers}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
        headers={"Access-Control-Allow-Origin": "*"},
    )
