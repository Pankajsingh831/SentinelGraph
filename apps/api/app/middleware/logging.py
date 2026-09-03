import structlog
import logging
from app.config import get_settings
from app.middleware.request_id import get_request_id

def inject_request_id(logger, log_method, event_dict):
    req_id = get_request_id()
    if req_id:
        event_dict["request_id"] = req_id
    return event_dict

def configure_logging():
    settings = get_settings()
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            inject_request_id,
            structlog.processors.JSONRenderer() if settings.LOG_LEVEL != 'DEBUG' else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )

def get_logger():
    return structlog.get_logger()
