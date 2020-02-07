
from django.conf.urls import include, url
from django.contrib.auth.decorators import login_required

from user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView

# from apps.user.views import

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 激活
    url(r'^login$', LoginView.as_view(), name='login'),  # 登录

    # url(r'^user$', login_required(UserInfoView.as_view()), name='user'),  # 用户信息页面
    # url(r'^order$', login_required(UserOrderView.as_view()), name='order'),  # 用户订单页面
    # url(r'^address$', login_required(AddressView.as_view()), name='address'),  # 用户地址信息页

    url(r'^user$', UserInfoView.as_view(), name='user'),  # 用户信息页面
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),  # 用户订单页面
    url(r'^address$', AddressView.as_view(), name='address'),  # 用户地址信息页
    url(r'^logout$', LogoutView.as_view(), name='logout'),  # 退出用户登录


]
