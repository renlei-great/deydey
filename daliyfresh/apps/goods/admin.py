from django.contrib import admin
from goods.models import GoodsType,GoodsSKU,Goods,IndexGoodsBanner,IndexPromotionBanner

# Register your models here.

admin.site.register(GoodsType)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexPromotionBanner)