from django.urls import path
from . import views
from .views import signup, login_view, logout_view,home
from .models import Detail
from .views import home,success 

urlpatterns = [
    path('', signup, name='signup'),   # ✅ home exists now
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', home, name='home'),
    path('success/', success, name='success'),
    path('login/', views.api_login),
    path('profile/', views.get_profile),
    path('profile/update/', views.update_profile),
]


