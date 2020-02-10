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
from alipay import AliPay
from daliyfresh import settings
import os

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
class CommitView1(View):
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
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    print('userid:%s,sku_id:%s' % (user.id, sku_id) )
                    import time
                    time.sleep(10)
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
            print(e)
            transaction.savepoint_rollback(save_1)
            return JsonResponse({'res': 7 , 'errmsg':'提交失败'})

        # todo: 删除redis中对应的商品
        conn.hdel(cart_key, *skus_id)

        transaction.savepoint_commit(save_1)

        # 返回数据
        return JsonResponse({'res': 5, 'message': '提交成功'})


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
                # 控制乐观锁的循环
                for i in range(3):
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

                    # todo: 增加销售量，减少库存量
                    # 获取旧库存
                    old_stock = sku.stock
                    new_sales = sku.sales + int(count)
                    new_stock = sku.stock - int(count)
                    # print('userid:%s,sku_id:%s, old_stock:%d' % (user.id, sku_id, old_stock))
                    # import time
                    # time.sleep(10)

                    # 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=old_stock).update(sales=new_sales, stock=new_stock)
                    if res == 0:
                        # print('userid:%s,sku_id:%s, res:%s' % (user.id, sku_id, res) )

                        if i >= 2 :
                            transaction.savepoint_rollback(save_1)
                            # print('userid:%s,sku_id:%s, res:%s, i:%s' % (user.id, sku_id, res, i))
                            return JsonResponse({'res': 7, 'errmsg': '提交失败'})
                        continue

                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=total,
                    )
                    break


            # todo: 更新订单页的总价和总量
            order.total_count = total_count
            order.total_price = total_price + transit_price
            order.save()
        except Exception as e:
            print(e)
            transaction.savepoint_rollback(save_1)
            return JsonResponse({'res': 7 , 'errmsg':'提交失败'})

        # todo: 删除redis中对应的商品
        conn.hdel(cart_key, *skus_id)

        transaction.savepoint_commit(save_1)

        # 返回数据
        return JsonResponse({'res': 5, 'message': '提交成功'})


class AliPayView(View):
    """支付宝付款"""
    def post(self, request):
        """付款请求"""
        # 获取用户
        user = request.user
        # 获取订单id
        order_id = request.POST.get('order_id')
        # 校验用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 校验订单id是否正确
        try:
            order_id = int(order_id)
        except Exception as e:
            return JsonResponse({'res':1, 'errmsg':'订单号不正确'})

        # 校验是否有该商品
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                order_status=1
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'没有此订单'})

        # 校验支付方式
        if not order.pay_method == 3:
            return JsonResponse({'res': 4, 'errmsg':'请使用支付宝支付'})

        # 处理业务
        print(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'))
        # 初始化 使用python sdk调用支付宝的接口，进行初始化接口类 todo: 特别注意与视频中的公钥地址配置不同，一定要结合文档去做
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016101800713274",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_price),
            subject='天天生鲜-%s' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 拼接引导用户去的网址 todo: 特别注意写成沙箱的地址
        alipay_order_url = "https://openapi.alipaydev.com/gateway.do?" + order_string

        # 返回数据
        return JsonResponse({'res': 3, 'messge': '成功', 'alipay_order_url': alipay_order_url})


class QueryView(View):
    """订单支付结果查询"""
    def post(self, request):
        """支付结果查询"""
        # 获取用户
        user = request.user
        # 获取订单id
        order_id = request.POST.get('order_id')
        # 校验用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 校验订单id是否正确
        try:
            order_id = int(order_id)
        except Exception as e:
            return JsonResponse({'res':1, 'errmsg':'订单号不正确'})

        # 校验是否有该商品
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                pay_method=3,
                order_status=1
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'ermsg':'没有此订单'})

        # 处理业务
        print(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'))
        # 初始化 使用python sdk调用支付宝的接口，进行初始化接口类 todo: 特别注意与视频中的公钥地址配置不同，一定要结合文档去做
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016101800713274",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        while True:
            # # create an order
            # alipay.api_alipay_trade_precreate(
            #     subject='天天生鲜-%s' % order_id,
            #     out_trade_no=order_id,
            #     total_amount=100
            # )

            # 调用查询函数,传入订单id
            response = alipay.api_alipay_trade_query(order_id)
            # 支付时会出现的三种状态：
            # 支付成功 表示：回复码：10000， 状态为成功
            # 支付进行中  表示：回复码40004（订单还未生成）受理失败，所以此时不会有订单状态这些，回复码10000（支付接口已被调用，但还未付款，状态为未付款）这个情况需要一直循环监听
            # 支付失败  其他情况都为失败
            '''
            respons = {
                "trade_no": "2017032121001004070200176844",   # 支付宝交易号
                "code": "10000",   # 网关返回码
                "invoice_amount": "20.00",
                "open_id": "20880072506750308812798160715407",
                "fund_bill_list": [
                  {
                    "amount": "20.00",
                    "fund_channel": "ALIPAYACCOUNT"
                  }
                ],
                "buyer_logon_id": "csq***@sandbox.com",
                "send_pay_date": "2017-03-21 13:29:17",
                "receipt_amount": "20.00",
                "out_trade_no": "out_trade_no15",
                "buyer_pay_amount": "20.00",
                "buyer_user_id": "2088102169481075",
                "msg": "Success",
                "point_amount": "0.00",
                "trade_status": "TRADE_SUCCESS",  # 交易状态
                "total_amount": "20.00"
            }
            '''
            if response.get('code') == '10000' and response.get('trade_status', "") == 'TRADE_SUCCESS':
                # 支付成功
                # 修改订单状态
                # print("成功")
                # for i, val in response.items():
                #     print(i, val)
                order.order_status = 4
                order.save()
                # 结果返回
                return JsonResponse({'res':3, 'mssage':'支付成功'})
            elif response.get('code') == '40004' or response.get('code') == '10000' and response.get('trade_status', "") == 'WAIT_BUYER_PAY':
                # 接口调用成功，等待付款
                # print("等待")
                # for i, val in response.items():
                #     print(i, val)
                import time
                time.sleep(5)
                continue
            else:
                # print(response.get('code', ""),response.get('trade_status'),response.get('invoice_amount'), order_id)
                # print("其他")
                # for i, val in response.items():
                #     print(i,val)
                return JsonResponse({'res':4, 'errmsg':'支付失败'})


class CommentInfoView(View):
    """评论视图"""
    def get(self, request, order_id):
        """显示添加评论页面"""
        return render(request, 'user_center_order_comment.html')




