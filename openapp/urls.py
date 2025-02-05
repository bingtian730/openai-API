from django.urls import path 
from openapp import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns=[
    path("", views.HomeView.as_view(), name='main'),
    path("sign-up/", views.SignUp.as_view(), name='signup'),
    path("delete/", views.DeleteHistory, name='deleteChat'),
    path("logout/", views.logout_view, name="logout"),
    path("login/", views.LoginView.as_view(), name="login"),
    path('admin/', admin.site.urls),
   
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)