
from django.conf.urls import include, url
from order.views import PlaceView, CommitView, AliPayView, QueryView, CommentInfoView

urlpatterns = [
    url(r'^place$', PlaceView.as_view(), name='place'),  # 显示订单页面
    url(r'^commit$', CommitView.as_view(), name='commit'),  # 处理订单页面提交
    url(r'^alipay$', AliPayView.as_view(), name='alipay'),  # 付款请求
    url(r'^query$', QueryView.as_view(), name='query'),  # 查询支付状态
    url(r'^comment/(?P<order_id>\d+)$', CommentInfoView.as_view(), name='comment'),  # 评论添加显示
]
