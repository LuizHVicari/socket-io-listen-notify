import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("API_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"

accesslog = "-"
errorlog = "-"
