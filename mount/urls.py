from django.urls import path
from . import views
from .views import signup, login_view, logout_view,home
from .models import detail

urlpatterns = [
    path('', signup, name='signup'),   # ✅ home exists now
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', home, name='home'),


]