from .views import VroomView
from .views2 import VroomView2
from .views_hatake import VroomView3
from django.urls import path

urlpatterns = [
    # url(r'', VroomView.as_view(), name="index"),
    path('view_route/', VroomView2.as_view(), name='index'),
    path('hatake/', VroomView3.as_view(), name='index_hatake'),

    path('', VroomView.as_view(), name='index'),
]
