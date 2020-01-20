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

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexTypeGoodsBanner
from django_redis import get_redis_connection
from django.template import loader

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

@app.task
def generete_index_html():
    """生成静态index.html文件"""
    # 获取商品分类
    types = GoodsType.objects.all()

    # 获取轮播图
    goods_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 获取促销活动栏
    prom_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取商品分类详情
    """去遍历GoodsSKU，看看效果是否会相同---------------------------------------------------？？？"""
    for type in types:
        # 获取每个类型中的所有详细商品信息 并给type加上这个查出来的属性
        # type.type_banner = GoodsSKU.objects.filter(type=type)   # 测试失败，他们市完全独立的两个表，分类表中包含了商品详情表，而不是指向商品详情表
        img_type_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
        # 获取文字展示信息
        text_type_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)
        # 给types中遍历出来的type添加图片展示属性
        type.img_type_banner = img_type_banner
        # 给types中遍历出来的type添加文字展示属性
        type.text_type_banner = text_type_banner

    # 组织模板上下文
    countext = {
        'types': types,
        'goods_banner': goods_banner,
        'prom_banner': prom_banner,
    }

    # 获取模板文件
    temp = loader.get_template("index_static.html")
    # 组织模板上下文并渲染模板文件
    temp_html = temp.render(countext)
    time.sleep(5)
    # 拼一个要写入的路径
    path_html = os.path.join(settings.BASE_DIR, 'static/index.html')
    # 写出一个静态的index.html文件
    with open(path_html, 'w') as f:
        f.write(temp_html)
