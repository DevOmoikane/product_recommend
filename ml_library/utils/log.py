import logging
import traceback
from typing import Optional, Any
import pprint

# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

def raiselog(exception: Exception, message: Optional[str] = None, print_traceback: bool = False):
    log_message = f"{message}: {str(exception)}" if message else str(exception)
    logger.error(log_message)
    # output stack trace for the exception
    logger.exception(exception)
    if print_traceback:
        logger.error(traceback.format_exc())
    raise exception

def logerror(message: str):
    logger.error(message)

def loginfo(message: str):
    logger.info(message)

def logdebug(message: str):
    logger.debug(message)

def logwarning(message: str):
    logger.warning(message)

def logcritical(message: str):
    logger.critical(message)

def logobject(obj: Any, message: Optional[str] = None):
    log_message = f"{message}: {pprint.pformat(obj)}" if message else pprint.pformat(obj)
    logger.info(log_message)
