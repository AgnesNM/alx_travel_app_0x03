import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app_0x03.settings')

# Create the Celery application instance
app = Celery('alx_travel_app_0x03')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix in Django settings.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Optional: Add a debug task for testing
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task for testing Celery setup.
    Usage: from myproject.celery import debug_task; debug_task.delay()
    """
    print(f'Request: {self.request!r}')
    return f'Debug task executed successfully!'

# Optional: Add error handler
@app.task(bind=True)
def error_handler(self, uuid):
    """
    Error handler task.
    """
    result = self.AsyncResult(uuid)
    print(f'Task {uuid} raised exception: {result.result!r}\n{result.traceback!r}')

# Configure Celery signals for better logging
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """
    Signal handler for task prerun.
    """
    logger.info(f'Task {task} (ID: {task_id}) is about to run with args: {args}, kwargs: {kwargs}')

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """
    Signal handler for task postrun.
    """
    logger.info(f'Task {task} (ID: {task_id}) completed with state: {state}, return value: {retval}')

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """
    Signal handler for task failure.
    """
    logger.error(f'Task {sender.name} (ID: {task_id}) failed: {exception}')
    logger.error(f'Traceback: {traceback}')

# Health check task
@app.task
def health_check():
    """
    Simple health check task to verify Celery is working.
    """
    return "Celery is working correctly!"

# Periodic task example (requires celery beat)
from celery.schedules import crontab

# You can add periodic tasks here
app.conf.beat_schedule = {
    'health-check-every-minute': {
        'task': 'alx_travel_app_0x03.celery.health_check',
        'schedule': crontab(minute='*'),  # Run every minute
        'options': {'queue': 'beat_tasks'}
    },
}

# Set default queue for beat tasks
app.conf.task_routes = {
    'alx_travel_app_0x03.celery.health_check': {'queue': 'beat_tasks'},
    'alx_travel_app_0x03.celery.debug_task': {'queue': 'debug_tasks'},
}
