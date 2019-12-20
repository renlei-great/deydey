from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from user.models import User
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from daliyfresh import settings
from celery_tasks.tasks import send_register_active_email
import re

# Create your views here.


class RegisterView(View):
    """注册的两种提交方式"""
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接受数据
        username = request.POST.get('user_name')  # 用户名
        pwd = request.POST.get('pwd')  # 密码
        cpwd = request.POST.get('cpwd')  # 确认密码
        email = request.POST.get('email')  # 邮箱
        allow = request.POST.get('allow')  # 是否同意条款
        # 验证数据
        if not all([username, pwd, cpwd, email]):
            return render(request, 'register.html', {'errmsg': '数据填写不完整'})

        # 验证用户名是否被注册过
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            # 用户名已经被注册
            return render(request, 'register.html', {'errmsg': '用户名已经被注册'})

        # 验证邮箱是否填写正确
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱填写不正确'})

        # 判断两次密码是否一致
        if not pwd == cpwd:
            return render(request, 'register.html', {'errmsg': '两次密码不一致'})

        # 判断是否同意条款
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意条款'})

        # 进行业务处理：保存数据
        user = User.objects.create_user(username, email, pwd)  # 使用django自带方法进行保存用户信息
        user.is_active = 0  # 修改为未激活
        user.save()

        # 对id进行加密
        serializer = Serializer(settings.SECRET_KEY, 3600)  # 创建一个加密功能类的对象
        info = {'user_id':user.id}
        res = serializer.dumps(info)
        # 对res转换字符串
        res = res.decode()  # 如果不对其进行utf8解码会出现错误，将二进制转为字符串
        # 发送邮件链接，包含激活练级：192.168.223.128:7788/user/active/1
        # 组织邮件发送内容
        # 主题
        # 用celery发送邮件
        send_register_active_email(username, res , email)
        # 重定向
        return redirect(reverse('goods:index'))


# user/active/1
class ActiveView(View):

    def get(self, request, token):
        """激活用户"""
        # 对token进行解密
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            tokens = serializer.loads(token)
        except SignatureExpired:
            return HttpResponse('验证过期')
        # 向数据库中写入数据
        user = User.objects.get(id = tokens['user_id'])
        user.is_active = 1
        user.save()

        # 返回登录界面
        return redirect(reverse('user:login'))


class LoginView(View):
    """登录界面"""
    def get(self,request):
        return render(request, 'login.html')

