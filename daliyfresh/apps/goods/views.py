from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexTypeGoodsBanner, Goods
from django_redis import get_redis_connection
from django.core.cache import cache
from order.models import OrderGoods
from django.core.paginator import Paginator


# Create your views here.

class IndexView(View):
    """首页显示视图"""

    def get(self, request):
        """url请求首页显示"""
        countext = cache.get('cache_index')
        if countext is None:
            print('设置缓存')
            # 获取商品分类
            types = GoodsType.objects.all()

            # 获取轮播图
            goods_banner = IndexGoodsBanner.objects.all().order_by('index')

            # 获取促销活动栏
            prom_banner = IndexPromotionBanner.objects.all().order_by('index')

            # 获取商品分类详情
            """去遍历GoodsSKU，看看效果是否会相同---------------------------------------------------？？？"""
            for type in types:
                # 获取每个类型中的所有详细商品信息 并给type加上这个查出来的属性
                # type.type_banner = GoodsSKU.objects.filter(type=type)   # 测试失败，他们市完全独立的两个表，分类表中包含了商品详情表，而不是指向商品详情表
                img_type_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
                # 获取文字展示信息
                text_type_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)
                # 给types中遍历出来的type添加图片展示属性
                type.img_type_banner = img_type_banner
                # 给types中遍历出来的type添加文字展示属性
                type.text_type_banner = text_type_banner

            # 组织模板上下文
            countext = {
                'types': types,
                'goods_banner': goods_banner,
                'prom_banner': prom_banner,
            }

            cache.set('cache_index', countext, 3600)

        # 获取购物车数目信息
        con = get_redis_connection('default')
        cart_count = 0
        user = request.user
        if user.is_authenticated():
            cart_id = "cart_%d" % user.id
            cart_count = con.hlen(cart_id)

        countext.update(cart_count=cart_count)

        return render(request, 'index.html', countext)


class DetailView(View):
    """商品详情页视图"""

    def get(self, request, goods_id):
        """显示详情页"""
        try:
            # 获取此商品详情
            goods_sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return redirect(reverse('goods:index'))
        # 获取商品分类
        types = GoodsType.objects.all()

        # 获取评论
        comments = OrderGoods.objects.filter(sku=goods_sku).exclude(comment='')
        # 获取新品推荐-只显示两个商品，使用切片
        new_goods = GoodsSKU.objects.filter(type=goods_sku.type).order_by('-create_time')[:2]

        #  获取此商品相同规格的商品
        goods_spu = GoodsSKU.objects.filter(goods=goods_sku.goods)  # .exclude(id=goods_id)

        # 获取购物车数目-添加历史浏览
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            con = get_redis_connection('default')
            cart_id = "cart_%d" % user.id
            cart_count = con.hlen(cart_id)

        # 组织模板上下文
        countext = {
            'types': types,
            'goods_sku': goods_sku,
            'comments': comments,
            'new_goods': new_goods,
            'cart_count': cart_count,
            'goods_spu': goods_spu,
        }

        # 添加用户浏览记录
        # 链接redis数据库
        con = get_redis_connection('default')
        # 拼接key
        history_key = "history_%s" % user.id
        # 移除以前浏览此商品的记录
        con.lrem(history_key, 0, goods_id)
        # 添加记录
        con.lpush(history_key, goods_id)

        return render(request, 'detail.html', countext)


# /goods/list
class ListView(View):
    """列表页"""

    def get(self, request, type_id, page):
        """显示列表页"""
        # 类型
        try:
            type = GoodsType.objects.get(id=type_id)
        except Exception as e:
            # 商品不存在返回首页
            return redirect(reverse('goods:index'))

        # 获取所有商品，选择要排序的方式
        sort = request.GET.get('sort')

        # 判断使用什么排序
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
            print('价格')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('id')
            sort = 'default'

        # 获取所有类型
        types = GoodsType.objects.all()

        # 获取新品推荐-只显示两个商品，使用切片
        new_goods = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 购物车
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            con = get_redis_connection('default')
            cart_id = "cart_%d" % user.id
            cart_count = con.hlen(cart_id)

        # 创建分页对象
        pag = Paginator(skus, 1)

        # 获取第page页的内容
        try:  # 进行容错处理
            page = int(page)
        except Exception as e:
            page = 1
        # 进行二次容错
        if page > pag.num_pages:
            page = 1
        # 获取内容
        skus_page = pag.page(page)

        # 控制页码始终五页
        # 总页数如果小于或等于五页，全部显示
        # 如果是前三页显示12345
        # 如果是后三页，显示后五页 8 9 10
        # 其他情况显示当前页前两页和后两页
        if skus_page.paginator.num_pages <= 5:
        # 总页数如果小于或等于五页，全部显示
            page_range = range(1,skus_page.paginator.num_pages+1)
        # 如果是前三页显示12345
        elif page <= 3 :
            page_range = range(1,6)
        # 如果是后三页，显示后五页 8 9 10
        elif pag.num_pages - page <= 2 :
            page_range = range(skus_page.paginator.num_pages-4,skus_page.paginator.num_pages+1)
        # 其他情况显示当前页前两页和后两页
        else:
            page_range = range(skus_page.paginator.num_pages - 2, skus_page.paginator.num_pages +3)

        # 组织上下文
        conutext = {
            'type': type,
            'types': types,
            'new_goods': new_goods,
            'cart_count': cart_count,
            'skus': skus,
            'sort': sort,
            'pag': pag,
            'skus_page': skus_page,
            'page_range': page_range,
        }

        # 返回数据
        return render(request, 'list.html', conutext)
