from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from utils.mixni import LofinRequiredMixni
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from user.models import Address

# Create your views here.

# /order/place
class PlaceView(LofinRequiredMixni, View):
    """订单页"""
    def post(self, request):
        """显示订单页面"""
        # 获取用户
        user = request.user
        # 获取商品id
        skus_id = request.POST.getlist('sku')

        # 校验数据
        if not skus_id:
            return

        # 处理业务
        # 拼接商品在redis存储的键名
        cart_key = 'cart_%s' % user.id
        # 链接redis
        conn = get_redis_connection('default')
        # 所有商品总金额和总件数
        total_count = 0
        total_price = 0
        # 存放所有商品
        skus = []
        # 遍历所有id进行查寻
        for sku_id in skus_id:
            # 商品
            sku = GoodsSKU.objects.get(id=sku_id)
            # 商品数量
            count = conn.hget(cart_key, sku_id)
            # 商品价钱小计
            total = sku.price * int(count)
            # 计算所有商品总金额和总件数
            total_count += int(count)
            total_price += total
            # 为sku动态添加件数，小计，总件数，总金额
            sku.count = count
            sku.total = total
            sku.total_count = total_count
            sku.total_price = total_price
            skus.append(sku)
        # 运费
        sku_frei = 10
        # 实付款
        payment = total_price + sku_frei

        # 查询收获地址
        addrs = Address.objects.filter(user=user)

        # 组织上下文
        countext = {
            'skus':skus,
            'sku_frei':sku_frei,
            'payment':payment,
            'addrs':addrs,
            'total_count':total_count,
            'total_price':total_price,
        }

        # 返回数据
        return render(request, 'place_order.html', countext)
