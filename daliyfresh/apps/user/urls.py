
from django.conf.urls import include, url

from user.views import RegisterView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 注册
]
