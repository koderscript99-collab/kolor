from django.urls import path
from . import views
from .views import signup, login_view, logout_view

urlpatterns = [
    path('', views.signup, name='home'),   # ✅ home exists now
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]