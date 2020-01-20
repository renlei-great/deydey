
from django.conf.urls import include, url

from goods.views import IndexView

urlpatterns = [
    url(r'^index$', IndexView.as_view(), name='index'),  # 首页

]
