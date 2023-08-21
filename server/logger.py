import structlog
import logging
import os
import time
from pprint import pprint


LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_TYPE = os.environ.get('LOG_TYPE', 'console')
logging.basicConfig(level=LOG_LEVEL, format='%(message)s')

__all__ = ('configure_logger', 'configure_falcon_logging_middleware', 'FORMAT_JSON', 'FORMAT_CONSOLE')

FORMAT_JSON = 'json'
FORMAT_CONSOLE = 'console'

def configure_logger(format=FORMAT_CONSOLE):
    """
        decides whethers logs are to be consumed in console format 
        or json format
    """
    if FORMAT_CONSOLE:
        structlog.configure(
            processors=[
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.CallsiteParameterAdder(
                    {
                        # structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        # structlog.processors.CallsiteParameter.LINENO,
                        structlog.processors.CallsiteParameter.MODULE,
                    }
                ),
                structlog.dev.ConsoleRenderer(pad_event=64),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    elif FORMAT_JSON:
        structlog.configure(
            processors=[
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.CallsiteParameterAdder(
                    {
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        structlog.processors.CallsiteParameter.MODULE,
                    }
                ),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )



def configure_falcon_logging_middleware():
    import falcon

    class Middleware():

        logger = structlog.get_logger(__name__)

        def process_request(self, req: "falcon.Request", *args, **kwargs):
            self.logger.info("Request:", x="Request1")

    return Middleware



class BaseLogger:

    @property
    def _logger(self):
        if not getattr(self, '__logger__', None):
            self.__logger__ = structlog.get_logger(type(self).__name__)
        return self.__logger__

    def _debug(self, msg, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, level="Debug", **kwargs)

    def _error(self, msg, *args, **kwargs) -> None:
        self._logger.error(msg, *args, level="Error", **kwargs)

    def _info(self, msg, *args, **kwargs) -> None:
        self._logger.info(msg, *args, level="Info", **kwargs)

    def _warning(self, msg, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, level="Warn", **kwargs)


class GunicornLogger:
    """
    A stripped down version of
        https://github.com/benoitc/gunicorn/blob/master/gunicorn/glogging.py
    to provide structlog logging in gunicorn

    Add the following to gunicorn start command to use this class::

        --logger-class app.common.logging.GunicornLogger
    """
    def __init__(self, cfg):
        configure_logger(format=LOG_TYPE)
        self._error_logger = structlog.get_logger('gunicorn.error')
        self._access_logger = structlog.get_logger('gunicorn.access')
        self.cfg = cfg

    def critical(self, msg, *args, **kwargs) -> None:
        self._error_logger.error(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs) -> None:
        self._error_logger.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs) -> None:
        self._error_logger.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs) -> None:
        self._access_logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs) -> None:
        self._access_logger.debug(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs) -> None:
        self._error_logger.exception(msg, *args, **kwargs)

    def log(self, lvl, msg, *args, **kwargs) -> None:
        self._access_logger.log(lvl, msg, *args, **kwargs)

    def access(self, resp, req, environ, request_time) -> None:
        atoms = self.atoms(resp, req, environ, request_time)
        log_message = "{remote_ip} - {request_string} {request_status} {response_length} {user_agent}".format(
            remote_ip=atoms["h"],
            request_string=atoms["r"],
            request_status=atoms["s"],
            response_length=atoms["b"],
            user_agent=atoms["a"]
        )
        self._access_logger.info(log_message)

    def reopen_files(self) -> None:
        pass # we don't support files

    def close_on_exec(self) -> None:
        pass # we don't support files

    def atoms(self, resp, req, environ, request_time):
        """ Gets atoms for log formatting.
        """
        status = resp.status
        if isinstance(status, str):
            status = status.split(None, 1)[0]
        atoms = {
            'h': environ.get('REMOTE_ADDR', '-'),
            'l': '-',
            'u': self._get_user(environ) or '-',
            't': self.now(),
            'r': "%s %s %s" % (environ['REQUEST_METHOD'],
                               environ['RAW_URI'],
                               environ["SERVER_PROTOCOL"]),
            's': status,
            'm': environ.get('REQUEST_METHOD'),
            'U': environ.get('PATH_INFO'),
            'q': environ.get('QUERY_STRING'),
            'H': environ.get('SERVER_PROTOCOL'),
            'b': getattr(resp, 'sent', None) is not None and str(resp.sent) or '-',
            'B': getattr(resp, 'sent', None),
            'f': environ.get('HTTP_REFERER', '-'),
            'a': environ.get('HTTP_USER_AGENT', '-'),
            'T': request_time.seconds,
            'D': (request_time.seconds * 1000000) + request_time.microseconds,
            'M': (request_time.seconds * 1000) + int(request_time.microseconds / 1000),
            'L': "%d.%06d" % (request_time.seconds, request_time.microseconds),
            'p': "<%s>" % os.getpid()
        }

        # add request headers
        if hasattr(req, 'headers'):
            req_headers = req.headers
        else:
            req_headers = req

        if hasattr(req_headers, "items"):
            req_headers = req_headers.items()

        atoms.update({"{%s}i" % k.lower(): v for k, v in req_headers})

        resp_headers = resp.headers
        if hasattr(resp_headers, "items"):
            resp_headers = resp_headers.items()

        # add response headers
        atoms.update({"{%s}o" % k.lower(): v for k, v in resp_headers})

        # add environ variables
        environ_variables = environ.items()
        atoms.update({"{%s}e" % k.lower(): v for k, v in environ_variables})

        return atoms
    
    def _get_user(self,environ):
        return None
    
    def now(self):
        """ return date in Apache Common Log Format """
        return time.strftime('[%d/%b/%Y:%H:%M:%S %z]')