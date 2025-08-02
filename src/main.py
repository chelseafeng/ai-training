import logging
import os
import sys

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from uvicorn.main import STARTUP_FAILURE
from uvicorn.supervisors import ChangeReload, Multiprocess

from config import log_config
from config.app_config import CONFIG, ROOT_PROJECT_DIR, STATIC_FILE_PATH
from controller import docs_router
from controller.paper_router import router as paper_router
from core.exception import global_exception, validation_exception
from core.exception.training_exception import TrainingException, training_exception_handler


exception_handlers = {
    Exception: global_exception.general_exception_handler,
    RequestValidationError: validation_exception.validation_exception_handler,
    HTTPException: global_exception.general_exception_handler,
    TrainingException: training_exception_handler,


}
middlewares = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]
app = FastAPI(
    exception_handlers=exception_handlers,
    middleware=middlewares,
    docs_url=None,
    redoc_url=None,
    swagger_ui_oauth2_redirect_url=None,
)
app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_FILE_PATH,
    ),
    name="static",
)
app.include_router(docs_router.router)
app.include_router(paper_router)
# app.include_router(document_chat_router.router)


if __name__ == "__main__":

    import uvicorn

    config = uvicorn.Config(
        "main:app",
        host=CONFIG["host"],
        port=CONFIG["port"],
        workers=CONFIG["workers"],
        reload=False,
    )
    server = uvicorn.Server(config)
    log_config.init_config()
    # 参考run方法实现
    if (config.reload or config.workers > 1) and not isinstance(app, str):
        logger = logging.getLogger("uvicorn.error")
        logger.warning(
            "You must pass the application as an import string to enable 'reload' or "
            "'workers'."
        )
        sys.exit(1)

    try:
        if config.should_reload:
            sock = config.bind_socket()
            ChangeReload(config, target=server.run, sockets=[sock]).run()
        elif config.workers > 1:
            sock = config.bind_socket()
            Multiprocess(config, target=server.run, sockets=[sock]).run()
        else:
            server.run()
    finally:
        if config.uds and os.path.exists(config.uds):
            os.remove(config.uds)  # pragma: py-win32

    if not server.started and not config.should_reload and config.workers == 1:
        sys.exit(STARTUP_FAILURE)
