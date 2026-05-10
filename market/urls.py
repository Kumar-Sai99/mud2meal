from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('',                  RedirectView.as_view(url='/home/')),
    path('home/',             views.home,             name='home'),
    path('register/',         views.register_view,    name='register'),
    path('login/',            views.login_view,       name='login'),
    path('logout/',           views.logout_view,      name='logout'),
    path('crops/',            views.crop_list,        name='crop_list'),
    path('crop/<int:pk>/',    views.crop_detail,      name='crop_detail'),
    path('dashboard/',        views.dashboard,        name='dashboard'),
    path('farmer-dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('buyer-dashboard/',  views.buyer_dashboard,  name='buyer_dashboard'),
    path('edit-profile/',     views.edit_profile,     name='edit_profile'),
    path('crop/<int:pk>/edit/', views.edit_crop, name='edit_crop'),
]