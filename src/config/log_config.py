import os
import sys
import logging
from types import FrameType
from typing import cast
from loguru import logger

def get_project_root() -> str:
    """获取项目根目录路径"""
    current_file_path = os.path.abspath(__file__)
    # 从 src/config/log_config.py 向上三级到项目根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))

# 计算日志路径
project_root = get_project_root()
log_path = os.path.join(project_root, "logs")
# 清空所有设置
logger.remove()
# 判断日志文件夹是否存在，不存则创建
if not os.path.exists(log_path):
    os.makedirs(log_path)
# 添加控制台输出的格式,sys.stdout为输出到屏幕;关于这些配置还需要自定义请移步官网查看相关参数说明
logger.add(sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss,SSS}</green> | "  # 颜色>时间
                       "{process.name} | "  # 进程名
                       "{thread.name} | "  # 进程名
                       "<cyan>{module}.{function}:{line}</cyan> | "  # 模块名.方法名:行号
                       "<level>{level}:{message}</level> "  # 等级:日志内容
                )
# 日志写入文件
logger.add(os.path.join(log_path,'fast_{time:YYYY-MM-DD}.log'),  # 写入目录指定文件
                format='{time:YYYY-MM-DD HH:mm:ss,SSS} - '  # 时间
                       "{process.name} | "  # 进程名
                       "{thread.name} | "  # 进程名
                       '{module}.{function}:{line} - {level} -{message}',  # 模块名.方法名:行号
                encoding='utf-8',
                retention='7 days',  # 设置历史保留时长
                backtrace=True,  # 回溯
                diagnose=True,  # 诊断
                enqueue=True,  # 异步写入
                rotation="00:00",  # 每日更新时间
                )

def init_config():
    # default_logger_names = [name for name in logging.root.manager.loggerDict] #全部的name
    default_logger_names = ['uvicorn.error','uvicorn','uvicorn.access'] #只修改uvicorn日志
    # 修改vuicorn日志的默认处理器
    logging.getLogger().handlers = [InterceptHandler()]
    for default_logger_name in default_logger_names:
        default_logger = logging.getLogger(default_logger_name)
        default_logger.propagate=False #禁止传播，防止日志重复记录
        default_logger.handlers = [InterceptHandler()]

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # 获取相应的loguru的日志级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage(),
        )

app_logger = logger

# 测试日志配置
if __name__ == "__main__":
    print(f"日志路径: {log_path}")
    app_logger.info("This is a test log")
    print("日志配置测试完成")

