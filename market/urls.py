from django.urls import path
from django.views.generic import RedirectView
from . import views, api_views

urlpatterns = [
    path('',                                   RedirectView.as_view(pattern_name='home')),
    path('home/',                              views.home,                  name='home'),
    path('join/',                              views.role_select,           name='role_select'),
    path('register/',                          views.register_view,         name='register'),
    path('login/',                             views.login_view,            name='login'),
    path('logout/',                            views.logout_view,           name='logout'),
    path('crops/',                             views.crop_list,             name='crop_list'),
    path('crop/<int:pk>/',                     views.crop_detail,           name='crop_detail'),
    path('crop/<int:crop_pk>/rate/',           views.submit_rating,         name='submit_rating'),
    path('crop/<int:crop_pk>/rate/delete/',    views.delete_rating,         name='delete_rating'),
    path('dashboard/',                         views.dashboard,             name='dashboard'),
    path('farmer-dashboard/',                  views.farmer_dashboard,      name='farmer_dashboard'),
    path('buyer-dashboard/',                   views.buyer_dashboard,       name='buyer_dashboard'),
    path('edit-profile/',                      views.edit_profile,          name='edit_profile'),
    path('crop/<int:pk>/edit/',                views.edit_crop,             name='edit_crop'),
    path('order/<int:pk>/',                    views.order_detail,          name='order_detail'),
    path('order/<int:pk>/update-status/',      views.update_order_status,   name='update_order_status'),
    path('orders/',                            views.my_orders,             name='my_orders'),
    path('cart/',                              views.cart_view,             name='cart'),
    path('cart/add/<int:crop_pk>/',            views.cart_add,              name='cart_add'),
    path('cart/remove/<int:crop_pk>/',         views.cart_remove,           name='cart_remove'),
    path('cart/update/<int:crop_pk>/',         views.cart_update,           name='cart_update'),
    path('cart/checkout/',                     views.cart_checkout,         name='cart_checkout'),
    path('order/success/',                     views.order_success,         name='order_success'),

    # REST API
    path('api/crops/',                         api_views.api_crop_list,         name='api_crop_list'),
    path('api/crops/featured/',                api_views.api_featured_crops,    name='api_featured_crops'),
    path('api/crops/<int:pk>/',                api_views.api_crop_detail,       name='api_crop_detail'),
    path('api/crops/district/<str:district>/', api_views.api_crops_by_district, name='api_crops_by_district'),
    path('api/categories/',                    api_views.api_category_list,     name='api_category_list'),
    path('api/my-crops/',                      api_views.api_my_crops,          name='api_my_crops'),
]

# Serve media and static files during development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)