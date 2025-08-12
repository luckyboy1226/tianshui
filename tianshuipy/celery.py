import os
from celery import Celery

# 设置Django默认配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings')

app = Celery('tianshuipy')

# 使用Django的设置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 