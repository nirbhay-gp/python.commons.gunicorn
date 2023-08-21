import os
import importlib
import multiprocessing
import gunicorn.app.base
import prometheus
import time


GUNICORN_WORKERS = os.environ.get('GUNICORN_WORKERS') or 3
GUNICORN_WORKER_CLASS = os.environ.get('GUNICORN_WORKER_CLASS') or 'gthread'
GUNICORN_THREADS = os.environ.get('GUNICORN_THREADS') or 4
GUNICORN_LOGGER = os.environ.get('GUNICORN_LOGGER') or 'logger.GunicornLogger'
GUNICORN_SERVICE_BINDS = os.environ.get('GUNICORN_SERVICE_BINDS') or '127.0.0.1:8001'
GUNICORN_PROMEHTHEUS_BINDS = os.environ.get('GUNICORN_PROMETHEUS_BINDS') or '127.0.0.1:9090'

def get_app():
    app_module = os.environ['GUNICORN_APP']
    module_name, obj_name = app_module.split(':')
    module = importlib.import_module(module_name)

    return getattr(module, obj_name, None)

def worker_exit(server, worker):
    from prometheus_client import multiprocess
    multiprocess.mark_process_dead(worker.pid)

def pre_request(worker, req):
    setattr(req, 'start_time', time.perf_counter())
    prometheus.metrics.http_incoming_requests.labels(host=req.remote_addr[0], method=req.method, path=req.path).inc()

def post_request(worker, req, environ, resp):
    labels = {
        'host': req.remote_addr[0], 
        'method': req.method, 
        'path': req.path, 
        'status': resp.status
    }
    prometheus.metrics.http_incoming_processed_requests.labels(**labels).inc()
    start_time = getattr(req, 'start_time', None)
    if start_time:
        prometheus.metrics.http_incoming_requests_processing_seconds.labels(**labels).observe(time.perf_counter() - start_time)


class Application(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

        self.cfg.set('worker_exit', worker_exit)
        self.cfg.set('pre_request', pre_request)
        self.cfg.set('post_request', post_request)
    
    def load(self):
        return self.application
    

if __name__ == '__main__':
    wsgi_app = get_app()
    wsgi_app = prometheus.metrics_app(wsgi_app)
    Application(wsgi_app, {
        'bind': GUNICORN_SERVICE_BINDS.split(",") + GUNICORN_PROMEHTHEUS_BINDS.split(','),
        'workers': GUNICORN_WORKERS,
        'worker_class': GUNICORN_WORKER_CLASS,
        'threads': GUNICORN_THREADS,
        'logger_class': GUNICORN_LOGGER,
    }).run()
