from cart.views import CartAddView, CartInfoView, UpdataView, DeleteView
from django.conf.urls import include, url

urlpatterns = [
    url(r'^add$', CartAddView.as_view(), name='add'),  # 添加购物车
    url(r'^$', CartInfoView.as_view(), name='show'),  # 显示购物车
    url(r'^update$', UpdataView.as_view(), name='update'),  # 更新数据库购物车
    url(r'^delete$', DeleteView.as_view(), name='delete'),  # 删除商品
]