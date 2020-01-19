# 使用celery对象
import time

from celery import Celery
from django.core.mail import send_mail

from daliyfresh import settings

# 在任务处理者那一端加
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daliyfresh.settings")
django.setup()


# 创建一个celery实例对象

app = Celery('celery_tasks.tasks', broker='redis://192.168.223.128:6379/8')  # 第一个参数为这个类命名，第二个参数是中间任务队列（broker）


# 定义任务函数，发送邮件
@app.task
def send_register_active_email(username, res, email ):
    """发送邮件"""
    subject = '注册激活'
    # html内容
    message = ''
    html_mag = '<h1>%s 欢迎您成为天天生鲜会员</h1><br>请点击下方链接激活会员<br><a href = "http://192.168.223.128:7788/user/active/%s">http://192.168.223.128:7788/user/active/%s </a><br >' % (
    username, res, res)
    # 收件人列表
    receiver = [email]
    # 发件人
    sender = settings.EMAIL_FROM

    # 发送
    send_mail(subject, message, sender, receiver, html_message=html_mag)
    time.sleep(5)
