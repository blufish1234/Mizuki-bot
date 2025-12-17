import logging
import inspect
import sys
from datetime import timedelta, timezone

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Set timezone to GMT+8
logger.configure(
    patcher=lambda record: record.update(
        time=record["time"].astimezone(timezone(timedelta(hours=8)))
    )
)
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
    "<b>|</b> <level>{level:<8}</level>"
    "<b>|</b> <b>[</b><blue>{module}</blue><b>]</b>"
    " <level>{message}</level>",
    diagnose=True,
    colorize=True,
)

# logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
