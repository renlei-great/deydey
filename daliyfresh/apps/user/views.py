from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from user.models import User
from django.core.urlresolvers import reverse
import re

# Create your views here.

"""def register(request):

    return render(request, 'register.html')


def register_handle(request):
    # 接受数据
    username = request.POST.get('user_name')  # 用户名
    pwd = request.POST.get('pwd')  # 密码
    cpwd = request.POST.get('cpwd')  # 确认密码
    email = request.POST.get('email')  # 邮箱
    allow = request.POST.get('allow')  # 是否同意条款
    # 验证数据
    if not all([username, pwd, cpwd, email, allow]):
        return render(request, 'register.html', {'errmsg': '数据填写不完整'})

    # 验证用户名是否被注册过
    try:
        user = User.objects.get(username = username)
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
    # if allow != 'no':
    #     return render(request, 'register.html')

    # 进行业务处理：保存数据
    user = User.objects.create_user(username, email, pwd)
    user.is_active = 0
    user.save()

    # 重定向
    return redirect(reverse('goods:index'))"""


class RegisterView(View):

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
        if not all([username, pwd, cpwd, email, allow]):
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
        # if allow != 'no':
        #     return render(request, 'register.html')

        # 进行业务处理：保存数据
        user = User.objects.create_user(username, email, pwd)
        user.is_active = 0
        user.save()

        # 重定向
        return redirect(reverse('goods:index'))