from rest_framework import serializers
from .models import Category, Crop, FarmerProfile


# ── CATEGORY SERIALIZER ───────────────────────────────
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'icon']


# ── FARMER SERIALIZER ─────────────────────────────────
class FarmerSerializer(serializers.ModelSerializer):
    username    = serializers.CharField(source='user.username')
    full_name   = serializers.CharField(source='user.get_full_name')
    email       = serializers.CharField(source='user.email')

    class Meta:
        model  = FarmerProfile
        fields = [
            'id', 'username', 'full_name', 'email',
            'phone', 'district', 'state',
            'bio', 'is_verified'
        ]


# ── CROP LIST SERIALIZER ──────────────────────────────
class CropListSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.user.get_full_name')
    farmer_id   = serializers.IntegerField(source='farmer.id')
    category    = CategorySerializer()
    photo_url   = serializers.SerializerMethodField()

    class Meta:
        model  = Crop
        fields = [
            'id', 'name', 'price', 'unit', 'quantity',
            'district', 'state', 'status', 'is_featured',
            'created_at', 'farmer_name', 'farmer_id',
            'category', 'photo_url',
        ]

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
        return None


# ── CROP DETAIL SERIALIZER ────────────────────────────
class CropDetailSerializer(serializers.ModelSerializer):
    farmer   = FarmerSerializer()
    category = CategorySerializer()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model  = Crop
        fields = [
            'id', 'name', 'description', 'price', 'unit',
            'quantity', 'location', 'district', 'state',
            'status', 'is_featured', 'created_at',
            'farmer', 'category', 'photo_url',
        ]

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
        return None


