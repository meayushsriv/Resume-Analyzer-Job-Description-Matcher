# Location: /src/worker/celery_app.py
from celery import Celery
from src.core.config import settings

# Create the Celery instance
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Tell Celery to find tasks in a file named 'tasks.py' inside 'src.worker'
celery_app.conf.imports = ("src.worker.tasks",)

print("--- Celery App Configured ---")