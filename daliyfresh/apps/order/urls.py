
from django.conf.urls import include, url
from order.views import PlaceView, CommitView

urlpatterns = [
    url(r'^place$', PlaceView.as_view(), name='place'),  # 显示订单页面
    url(r'^commit$', CommitView.as_view(), name='commit')  # 处理订单页面提交
]
