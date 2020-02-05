from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixni import LofinRequiredMixni

# Create your views here.

class CartAddView(View):
    """购物车新增视图"""
    def post(self,request):
        # 获取数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 获取当前用户
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录,请先登录'})

        # 校验数据
        # 校验数据的完整性
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg':'数据不完整'})
        # 校验数量是否正确
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg':'数量不正确'})
        # 校验是否有此商品

        try:
            sku = GoodsSKU.objects.get(id= sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg':'没有此商品'})

        # 处理业务
        # 链接redis数据库
        conn = get_redis_connection('default')
        # 拼接购物车存储的key
        cart_key = "cart_%s" % user.id
        # 获取以前此商品添加的数量,和此刻要添加的数量进行累加
        old_count = conn.hget(cart_key, sku_id)
        if old_count:
            count += int(old_count)
        # 校验商品的数量是否超过了库存
        stock = sku.stock
        if count > stock:
            # 购买数量超过库存
            return JsonResponse({'res':4, 'errmsg':'库存不足'})

        # 添加购物车记录
        conn.hset(cart_key, sku_id, count)

        # 获取添加了几件商品
        len_cart = conn.hlen(cart_key)

        # 返回数据
        return JsonResponse({'res': 5, 'message':'添加成功', 'len_cart':len_cart})


class CartInfoView(LofinRequiredMixni, View):
    """购物车视图"""
    # /cart/show
    def get(self, request):
        """显示"""
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%s' % user.id
        # 取出此用户购物车的所有商品，以字典形式返回
        dict_sku = conn.hgetall(cart_key)
        # 定义总件数和总价
        total_count = 0
        total_price = 0
        # 定义存放所有购物车商品
        skus = []
        # 遍历出来所有的商品以及数量
        for sku_id, count in dict_sku.items():
            # 查出每一个商品，进行动态添加小计和件数属性
            sku = GoodsSKU.objects.get(id=sku_id)
            sku.total = sku.price * int(count)
            sku.count = count
            # 计算总价钱和总数量
            total_count += int(count)
            total_price += sku.total
            skus.append(sku)

        # 组织模板上下文
        countext = {
            'skus':skus,
            'total_count':total_count,
            'total_price': total_price,
        }




        return render(request, 'cart.html', countext)


class UpdataView(View):
    """购物车更新"""
    def post(self, request):
        """购物车页面进行增加"""
        # 获取数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 获取当前用户
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录,请先登录'})

        # 校验数据
        # 校验数据的完整性
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 校验数量是否正确
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数量不正确'})
        # 校验是否有此商品

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '没有此商品'})

        # 处理业务
        # 链接redis数据库
        conn = get_redis_connection('default')
        # 拼接购物车存储的key
        cart_key = "cart_%s" % user.id
        # 校验商品的数量是否超过了库存
        stock = sku.stock
        if count > stock:
            # 购买数量超过库存
            return JsonResponse({'res': 4, 'errmsg': '库存不足'})

        # 添加到数据库
        conn.hset(cart_key, sku_id, count)

        # 计算总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回数据
        return JsonResponse({'res':5, 'total_count': total_count, 'message': '添加成功'})

# 需要接受数据商品id
# /cart/delete
class DeleteView(View):
    """删除商品"""
    def post(self, request):
        """删除"""
        # 获取当前用户
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录,请先登录'})

        # 接受数据
        sku_id = request.POST.get('sku_id')

        # 校验数据
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '商品id无效'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg' : '商品不存在'})

        # 处理业务
        conn = get_redis_connection('default')
        # 组织键名
        cart_key = 'cart_%s' % user.id
        # 执行删除
        conn.hdel(cart_key, sku_id)

        # 计算总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回数据
        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功'})

























