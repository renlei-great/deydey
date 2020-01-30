# 定义类引用
from haystack import indexes
# 导入要使用的类模型
from goods.models import GoodsSKU


#指定对于某个类的某些数据建立索引

class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()