from django.urls import path
from django.views.generic import RedirectView
from . import views, api_views

urlpatterns = [
    # ── NORMAL PAGES ──────────────────────────────────
    path('',                    RedirectView.as_view(url='/home/')),
    path('home/',               views.home,             name='home'),
    path('join/',               views.role_select,      name='role_select'),
    path('register/',           views.register_view,    name='register'),
    path('login/',              views.login_view,       name='login'),
    path('logout/',             views.logout_view,      name='logout'),
    path('crops/',              views.crop_list,        name='crop_list'),
    path('crop/<int:pk>/',      views.crop_detail,      name='crop_detail'),
    path('dashboard/',          views.dashboard,        name='dashboard'),
    path('farmer-dashboard/',   views.farmer_dashboard, name='farmer_dashboard'),
    path('buyer-dashboard/',    views.buyer_dashboard,  name='buyer_dashboard'),
    path('edit-profile/',       views.edit_profile,     name='edit_profile'),
    path('crop/<int:pk>/edit/', views.edit_crop,        name='edit_crop'),
    path('chat/<int:room_id>/',  views.chat_room,  name='chat_room'),
    path('start-chat/<int:crop_pk>/', views.start_chat, name='start_chat'),

    # ── API ENDPOINTS ──────────────────────────────────
    path('api/crops/',                        api_views.api_crop_list,        name='api_crop_list'),
    path('api/crops/featured/',               api_views.api_featured_crops,   name='api_featured_crops'),
    path('api/crops/<int:pk>/',               api_views.api_crop_detail,      name='api_crop_detail'),
    path('api/crops/district/<str:district>/',api_views.api_crops_by_district,name='api_crops_by_district'),
    path('api/categories/',                   api_views.api_category_list,    name='api_category_list'),
    path('api/my-crops/',                     api_views.api_my_crops,         name='api_my_crops'),
    path('api/my-enquiries/',                 api_views.api_my_enquiries,     name='api_my_enquiries'),
]