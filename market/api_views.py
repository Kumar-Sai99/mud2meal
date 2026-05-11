from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Crop, Category, Enquiry, FarmerProfile
from .serializers import (
    CropListSerializer, CropDetailSerializer,
    CategorySerializer, EnquirySerializer
)


# ── CROP LIST API ─────────────────────────────────────
@api_view(['GET'])
def api_crop_list(request):
    """
    GET /api/crops/
    Returns all available crops.
    Optional filters: ?q=name  ?category=id  ?district=name
    """
    crops = Crop.objects.filter(
        status='available'
    ).select_related('farmer__user', 'category')

    # filters
    query    = request.GET.get('q', '')
    category = request.GET.get('category', '')
    district = request.GET.get('district', '')

    if query:
        crops = crops.filter(name__icontains=query)
    if category:
        crops = crops.filter(category__id=category)
    if district:
        crops = crops.filter(district__icontains=district)

    serializer = CropListSerializer(
        crops, many=True, context={'request': request}
    )
    return Response({
        'count' : crops.count(),
        'crops' : serializer.data,
    })


# ── CROP DETAIL API ───────────────────────────────────
@api_view(['GET'])
def api_crop_detail(request, pk):
    """
    GET /api/crops/<pk>/
    Returns single crop details.
    """
    crop = get_object_or_404(
        Crop.objects.select_related('farmer__user', 'category'), pk=pk
    )
    serializer = CropDetailSerializer(crop, context={'request': request})
    return Response(serializer.data)


# ── CATEGORY LIST API ─────────────────────────────────
@api_view(['GET'])
def api_category_list(request):
    """
    GET /api/categories/
    Returns all categories.
    """
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


# ── FEATURED CROPS API ────────────────────────────────
@api_view(['GET'])
def api_featured_crops(request):
    """
    GET /api/crops/featured/
    Returns featured crops only.
    """
    crops = Crop.objects.filter(
        is_featured=True, status='available'
    ).select_related('farmer__user', 'category')

    serializer = CropListSerializer(
        crops, many=True, context={'request': request}
    )
    return Response({
        'count': crops.count(),
        'crops': serializer.data,
    })


# ── CROPS BY DISTRICT API ─────────────────────────────
@api_view(['GET'])
def api_crops_by_district(request, district):
    """
    GET /api/crops/district/<district>/
    Returns crops from a specific district.
    """
    crops = Crop.objects.filter(
        status='available', district__icontains=district
    ).select_related('farmer__user', 'category')

    serializer = CropListSerializer(
        crops, many=True, context={'request': request}
    )
    return Response({
        'district': district,
        'count'   : crops.count(),
        'crops'   : serializer.data,
    })


# ── FARMER CROPS API ──────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_crops(request):
    """
    GET /api/my-crops/
    Returns logged-in farmer's crops.
    Requires login.
    """
    try:
        farmer = request.user.farmer
    except:
        return Response(
            {'error': 'Only farmers can access this.'},
            status=status.HTTP_403_FORBIDDEN
        )

    crops      = Crop.objects.filter(farmer=farmer).select_related('category')
    serializer = CropListSerializer(crops, many=True, context={'request': request})
    return Response({
        'farmer': request.user.username,
        'count' : crops.count(),
        'crops' : serializer.data,
    })


# ── ENQUIRIES API ─────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_enquiries(request):
    """
    GET /api/my-enquiries/
    Returns logged-in farmer's enquiries.
    Requires login.
    """
    try:
        farmer = request.user.farmer
    except:
        return Response(
            {'error': 'Only farmers can access this.'},
            status=status.HTTP_403_FORBIDDEN
        )

    enquiries  = Enquiry.objects.filter(
        crop__farmer=farmer
    ).select_related('buyer__user', 'crop').order_by('-created')
    serializer = EnquirySerializer(enquiries, many=True)
    return Response({
        'count'    : enquiries.count(),
        'enquiries': serializer.data,
    })