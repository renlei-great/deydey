from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from utils.mixni import LofinRequiredMixni
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from user.models import Address
from django.http import JsonResponse
from order.models import OrderInfo, OrderGoods
from datetime import datetime
from django.db import  transaction

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
        # 将列表中存放的商品id变为字符串
        str_id = ",".join(skus_id)
        # 组织上下文
        countext = {
            'skus':skus,
            'sku_frei':sku_frei,
            'payment':payment,
            'addrs':addrs,
            'total_count':total_count,
            'total_price':total_price,
            'str_id': str_id
        }

        # 返回数据
        return render(request, 'place_order.html', countext)


# /order/commit
class CommitView(View):
    """订单处理"""
    @transaction.atomic
    def post(self, request):
        """提交订单"""

        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg':'用户未登录'})
        # 获取数据
        # 获取字符串商品id
        str_id = request.POST.get('str_id')
        # 获取支付方式
        pay_method = request.POST.get('pay_method')
        # 获取收获地址id
        addr_id = request.POST.get('addr_id')

        # 校验数据
        if not all([str_id,pay_method,addr_id]):
            return JsonResponse({'res': 1, 'errmsg':'数据不完整'})

        # 校验支付方式是否正确
        if pay_method is OrderInfo.DICT_METHOD_CHOICES.keys:
            return JsonResponse({'res': 2, 'errmsg':'支付方式不正确'})

        # 校验地址是否正确
        try:
            address = Address.objects.get(id= addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg':'收获不正确'})

        # todo: 处理核心逻辑
        # 组织订单id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 商品数量和商品总价
        total_count = 0
        total_price = 0
        # 订单运费
        transit_price = 10
        # todo: 设置事物保存点，如果有失败旧回滚到这个保存点
        save_1 = transaction.savepoint()
        try:
            # todo: 向数据库中增加数据
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user, addr=address,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price,
            )
            # todo: 向商品详情页中添加商品信息
            # 获取字符串中的商品id
            skus_id = str_id.split(",")
            cart_key = 'cart_%d' % user.id
            # 链接redis
            conn = get_redis_connection('default')
            for sku_id in skus_id:
                try:
                    # 获取商品
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(save_1)
                    return JsonResponse({'res': 4, 'errmsg':'商品不存在'})
                # 商品价格
                price = sku.price
                # 商品数量
                count = conn.hget(cart_key, sku_id)
                # todo: 判断商品库存是否够
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_1)
                    return JsonResponse({'res':6, 'errmsg':'商品库存不足'})
                # 计算小计价格
                total = price * int(count)
                # 计算商品总价和总件数
                total_count += int(count)
                total_price += total
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=total,
                )
                # todo: 增加销售量，减少库存量
                sku.sales += int(count)
                sku.stock -= int(count)
                sku.save()

            # todo: 更新订单页的总价和总量
            order.total_count = total_count
            order.total_price = total_price + transit_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_1)
            return JsonResponse({'res': 7 , 'errmsg':'提交失败'})

        # todo: 删除redis中对应的商品
        conn.hdel(cart_key, *skus_id)

        transaction.savepoint_commit(save_1)

        # 返回数据
        return JsonResponse({'res': 5, 'message': '提交成功'})

