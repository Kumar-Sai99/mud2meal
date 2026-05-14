from django.contrib import admin
from .models import Category, FarmerProfile, BuyerProfile, Crop, Rating, Order, Cart

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ['id', 'crop', 'buyer', 'farmer', 'quantity', 'total_price', 'status', 'delivery', 'payment', 'created_at']
    list_filter   = ['status', 'delivery', 'payment']
    search_fields = ['crop__name', 'buyer__user__username', 'farmer__user__username']
    ordering      = ['-created_at']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'crop', 'quantity', 'added_at']

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display  = ['name', 'farmer', 'category', 'price', 'unit', 'status', 'is_featured', 'created_at']
    list_filter   = ['status', 'category', 'is_featured']
    search_fields = ['name', 'farmer__user__username']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']

@admin.register(FarmerProfile)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'district', 'state', 'is_verified', 'upi_id']

@admin.register(BuyerProfile)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'district', 'state']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['crop', 'buyer', 'stars', 'created']