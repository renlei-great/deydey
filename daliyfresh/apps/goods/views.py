from django.shortcuts import render
from django.views.generic import View
from django.core.urlresolvers import reverse
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexTypeGoodsBanner
from django_redis import get_redis_connection
from django.core.cache import cache

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
            cart_id = "cart_%d" %user.id
            cart_count = con.hlen(cart_id)

        countext.update(cart_count=cart_count)

        return render(request, 'index.html', countext)