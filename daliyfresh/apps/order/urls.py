
from django.conf.urls import include, url
from order.views import PlaceView

urlpatterns = [
    url(r'^place$', PlaceView.as_view(), name='place')
]
