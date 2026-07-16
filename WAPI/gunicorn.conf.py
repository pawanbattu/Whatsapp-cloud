bind = "0.0.0.0:8000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "./logs/access_gunicorn.log"
errorlog = "./logs/error_gunicorn.log"

capture_output = True
loglevel = "debug"