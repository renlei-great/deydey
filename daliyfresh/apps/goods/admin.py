from django.contrib import admin
from goods.models import GoodsType,GoodsSKU,Goods,IndexGoodsBanner,IndexPromotionBanner
from django.core.cache import cache

# Register your models here.

class BaseMangeModels(admin.ModelAdmin):
    """当出现改变或删除首页内容市重新生成首页静态文件"""
    def save_model(self, request, obj, form, change):
        """修改"""
        # 实现父类中该方法的功能
        super().save_model(request, obj, form, change)

        # 生成新的静态文件
        from celery_tasks.tasks import generete_index_html
        generete_index_html.delay()

        # 页面进行修改后，清除cache首页缓存
        cache.delete('cache_index')

    def delete_model(self, request, obj):
        # 实现父类中该方法的功能
        super().delete_model(request, obj)

        # 生成新的金泰文件
        from celery_tasks.tasks import generete_index_html
        generete_index_html.delay()

        # 页面内容有所删除时，清除cache首页缓存
        cache.delete('cache_index')


admin.site.register(GoodsType, BaseMangeModels)
admin.site.register(GoodsSKU, BaseMangeModels)
admin.site.register(Goods, BaseMangeModels)
admin.site.register(IndexGoodsBanner, BaseMangeModels)
admin.site.register(IndexPromotionBanner, BaseMangeModels)