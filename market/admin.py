from django.contrib import admin
from .models import Category, FarmerProfile, BuyerProfile, Crop, Enquiry, EnquiryReply


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'icon']
    search_fields = ['name']


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'phone', 'district', 'state', 'is_verified']
    search_fields = ['user__username', 'district']
    list_filter   = ['is_verified', 'state']


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'phone', 'district', 'state']
    search_fields = ['user__username', 'district']


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display  = ['name', 'farmer', 'category', 'price', 'unit', 'district', 'status', 'is_featured']
    search_fields = ['name', 'farmer__user__username', 'district']
    list_filter   = ['status', 'is_featured', 'category', 'state']


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display  = ['buyer', 'crop', 'phone', 'created', 'is_read']
    search_fields = ['buyer__user__username', 'crop__name']
    list_filter   = ['is_read']


@admin.register(EnquiryReply)
class EnquiryReplyAdmin(admin.ModelAdmin):
    list_display  = ['enquiry', 'created']