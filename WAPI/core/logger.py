import logging
import inspect
import json

logger = logging.getLogger("app_logger")

def app_logs(log_level, message, context=None):
    frame = inspect.currentframe().f_back
    method_name = frame.f_code.co_name
    line_number = frame.f_lineno
    context_str = json.dumps(context, default=str) if context else ""
    log_message = f"[{method_name}:{line_number}] {message} | Context: {context_str}"
    log_level = log_level.casefold()

    if log_level == "DEBUG".casefold():
        logger.debug(log_message)
    elif log_level == "INFO".casefold():
        logger.info(log_message)
    elif log_level == "WARNING".casefold():
        logger.warning(log_message)
    elif log_level == "ERROR".casefold():
        logger.error(log_message)
    elif log_level == "CRITICAL".casefold():
        logger.critical(log_message)
    elif log_level == 'EXCEPTION'.casefold():
        logger.exception(log_message)
