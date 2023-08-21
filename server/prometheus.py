import os
import structlog
import prometheus_client as prometheus
import prometheus_client.multiprocess as prometheus_multiprocess

logger = structlog.get_logger(__name__)

registry = prometheus.CollectorRegistry()
prometheus.ProcessCollector(registry=registry)

if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
    logger.info("prometheus: multiproc enabled")
    prometheus_multiprocess.MultiProcessCollector(registry)

__metrics = (
    ('Counter', 'http_incoming_requests', 'Total HTTP Requests', ("method", "path", "host")), 
    ('Counter', 'http_incoming_processed_requests', 'Total HTTP Requests Processed', ("method", "path", "host", "status")),
    ('Summary', 'http_incoming_requests_processing_seconds', 'Time spent processing request', ("method", "path", "host", "status")),
    ('Summary', 'http_incoming_requests_payload_size', 'Request Payload Size', ("method", "path", "host", "status")),
)

class Metrics:

    def __init__(self, metric_list):
        for item in metric_list:
            metric = getattr(prometheus, item[0], None).__call__(item[1], item[2], labelnames=item[3])
            setattr(self, item[1], metric)


metrics = Metrics(__metrics)

def handle_metrics_response(environ, start_response):
    data = prometheus.generate_latest(registry)
    status = '200 OK'
    response_headers = [
        ('Content-type', prometheus.CONTENT_TYPE_LATEST),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return iter([data])

def metrics_app(application):
    def handler(environ, start_response):
        request_path = environ.get('PATH_INFO')
        server_port = environ.get('SERVER_PORT')
        
        if request_path == '/_metrics' and server_port == '9090':
            return handle_metrics_response(environ, start_response)
        
        return application.__call__(environ, start_response)
    return handler
