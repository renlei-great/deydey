from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from user.models import User, Address
from goods.models import GoodsSKU
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from daliyfresh import settings
from celery_tasks.tasks import send_register_active_email
import re
from django.contrib.auth import authenticate, login, logout
from utils.mixni import LofinRequiredMixni
from django_redis import get_redis_connection


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
        # 用celery发送邮件这个函数被装饰后有一个delay方法，用这个方法加入到broker队列中
        send_register_active_email.delay(username, res , email)
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
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            # 记住密码
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            # 不记住密码
            username = ''
            # 将复选框设为不记住
            checked = ''
        return render(request, 'login.html', {'username':username, 'checked':checked})

    def post(self, request):
        """验证登录"""
        # 接受用户的信息
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        checked = request.POST.get('checked')

        # 验证信息完整性
        if not all([username, pwd]):
            return render(request, 'login.html', {'errmsg': '请填写完整'})

        # django自带验证用户名和密码的函数authenticate
        user = authenticate(username=username, password=pwd)
        if user is not None:
            # 密码用户名正确
            if user.is_active:
                # 用户已激活
                # 保存用户登录状态
                login(request, user)
                # 保存response子类

                # 获取request中next的地址,默认跳转到index页面
                get_heml = request.GET.get('next', reverse("goods:index"))
                response = redirect(get_heml)
                if checked == 'on':
                    # 设置一个cooke
                    response.set_cookie('username', username, max_age= 7*24*3600)
                    # 返回
                    return response
                else:
                    # 删除session
                    response.delete_cookie('username')
                    # 跳转到首页
                    return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            # 用户密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码不正确'})


        # 进行业务处理：去数据库进行查询比对

        # 返回给用户


class LogoutView(View):
    def get(self, request):
        # 退出用户登录清除sessions信息
        logout(request)

        # 清除完sessions信息后跳转回首页
        return redirect(reverse('goods:index'))


# /user/user
class UserInfoView(LofinRequiredMixni,View):
    """用户中心-信息页"""
    def get(self,request):
        """显示"""
        # 获取用户
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户最近浏览的五条信息
        # 链接到redis缓存数据库,获取用户最近浏览的五条信息，也就是说从redis数据库中取
        # 具体理解就是历史记录因为用户经常用到，所以用redis做缓存，存入每个商品的id到redis数据库中，取的时候，县从redis数据库中取出前五个商品id，然后再用这五个id到mysql数据库中取出
        # 详细的商品信息
        con = get_redis_connection("default")  # redis的一个实例对象，链接redis数据库

        # 拼接列表名
        history_key = "history_%s" % user.id

        # 查询最近浏览的五个id
        sku_ids = con.lrange(history_key,0,4)

        # 遍历从数据库中查出商品具体详细信息
        goos_li = []
        for sku in sku_ids:
            id_sku = GoodsSKU.objects.get(id = sku)
            goos_li.append(id_sku)
        # 组织上下文
        content = {'prm': 'user',
                   'user':user,
                   'address': address,
                   'goos_li':goos_li,}
        # prm:user
        return render(request, 'user_center_info.html', content)


# /user/order
class UserOrderView(LofinRequiredMixni,View):
    """用户中心-订单页"""
    def get(self, request):
        """显示"""
        # prm:order
        return render(request, 'user_center_order.html', {'prm':'order'})


# /user/address
class AddressView(LofinRequiredMixni,View):
    """用户中心-地址页"""
    def get(self, request):
        """显示"""
        # 获取默认收获地址
        user = request.user
        address = Address.objects.get_default_address(user)
        # prm:address
        return render(request, 'user_center_site.html', {'prm':'address', "address": address})

    def post(self, request):
        """保存地址post请求"""
        # 接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        print(receiver,addr,zip_code,phone)
        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, "user_center_site.html", {"errmsg":"数据不完整"})

        try:
            if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
                return render(request, "user_center_site.html", {"errmsg":"电话号填写不正确"})
        except Exception:
                return render(request, "user_center_site.html", {"errmsg": "请输入正确的电话号"})

        # 处理业务：保存收获地址
        user = request.user
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user = user,receiver = receiver,addr = addr,zip_code = zip_code,phone = phone,is_default = is_default)
        # 返回数据
        return redirect(reverse("user:address"))
