from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Avg

from .models import (
    Crop, Category, FarmerProfile, BuyerProfile,
    Enquiry, EnquiryReply, ChatRoom, ChatMessage,
    Rating, Wishlist, Order,
)
from .forms import RegisterForm, LoginForm, CropForm, EnquiryForm


# ── HOME ─────────────────────────────────────────────
def home(request):
    featured_crops = Crop.objects.filter(is_featured=True, status='available').select_related('farmer__user', 'category')
    all_crops      = Crop.objects.filter(status='available').select_related('farmer__user', 'category')
    categories     = Category.objects.all()
    total_crops    = Crop.objects.filter(status='available').count()
    total_farmers  = FarmerProfile.objects.count()
    total_buyers   = BuyerProfile.objects.count()

    return render(request, 'market/home.html', {
        'featured_crops': featured_crops,
        'all_crops'     : all_crops,
        'categories'    : categories,
        'total_crops'   : total_crops,
        'total_farmers' : total_farmers,
        'total_buyers'  : total_buyers,
    })

def home(request):
    featured_crops = Crop.objects.filter(
        is_featured=True, status='available'
    ).select_related('farmer__user', 'category')

    all_crops = Crop.objects.filter(
        status='available'
    ).select_related('farmer__user', 'category')

    categories  = Category.objects.all()
    total_crops = Crop.objects.filter(status='available').count()

    # ← add districts
    raw_districts = Crop.objects.filter(
        status='available'
    ).values_list('district', flat=True)
    districts = sorted(set(d.strip() for d in raw_districts if d.strip()))

    is_farmer = False
    if request.user.is_authenticated:
        try:
            request.user.farmer
            is_farmer = True
        except:
            is_farmer = False

    return render(request, 'market/home.html', {
        'featured_crops': featured_crops,
        'all_crops'     : all_crops,
        'categories'    : categories,
        'total_crops'   : total_crops,
        'districts'     : districts,    # ← add this
        'is_farmer'     : is_farmer,
    })


# ── REGISTER ─────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('/home/')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data['username'], email=data['email'],
                password=data['password1'],
                first_name=data['first_name'], last_name=data['last_name'],
            )
            if data['role'] == 'farmer':
                FarmerProfile.objects.create(user=user, phone=data['phone'], district=data['district'], state=data['state'])
            else:
                BuyerProfile.objects.create(user=user, phone=data['phone'], district=data['district'], state=data['state'])
            login(request, user)
            messages.success(request, f"Welcome to Mud2Meal, {user.first_name}! 🎉")
            return redirect('/home/')
        else:
            for field, errors in form.errors.items():
                messages.error(request, errors[0]); break
    else:
        form = RegisterForm()
    return render(request, 'market/register.html', {'form': form})


# ── LOGIN ─────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/home/')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name}! 👋")
                return redirect('/home/')
            messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please fill in all fields.')
    else:
        form = LoginForm()
    return render(request, 'market/login.html', {'form': form})


# ── LOGOUT ───────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out. See you soon! 👋")
    return redirect('/home/')


# ── ROLE SELECT ──────────────────────────────────────
def role_select(request):
    if request.user.is_authenticated:
        return redirect('/home/')
    return render(request, 'market/role_select.html')


# ── DASHBOARD ROUTER ─────────────────────────────────
@login_required
def dashboard(request):
    try: request.user.farmer; return redirect('/farmer-dashboard/')
    except: pass
    try: request.user.buyer; return redirect('/buyer-dashboard/')
    except: pass
    return redirect('/home/')


# ── CROP LIST ────────────────────────────────────────
def crop_list(request):
    query    = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    district = request.GET.get('district', '')
    sort     = request.GET.get('sort', '-created_at')

    if sort not in ['-created_at', 'created_at', 'name', '-name']:
        sort = '-created_at'

    crops = Crop.objects.filter(status='available').select_related('farmer__user', 'category')
    if query:    crops = crops.filter(name__icontains=query)
    if category: crops = crops.filter(category__id=category)
    if district: crops = crops.filter(district__icontains=district)
    crops = crops.order_by(sort)

    paginator = Paginator(crops, 12)
    crops     = paginator.get_page(request.GET.get('page', 1))

    categories = Category.objects.all()
    raw_d      = Crop.objects.filter(status='available').values_list('district', flat=True)
    districts  = sorted(set(d.strip() for d in raw_d if d.strip()))

    return render(request, 'market/crop_list.html', {
        'crops': crops, 'categories': categories, 'districts': districts,
        'query': query, 'category': category, 'district': district, 'sort': sort,
    })


# ── CROP DETAIL ──────────────────────────────────────
def crop_detail(request, pk):
    crop    = get_object_or_404(Crop.objects.select_related('farmer__user', 'category'), pk=pk)
    related = Crop.objects.filter(category=crop.category, status='available').exclude(pk=pk).select_related('farmer__user')[:4]
    ratings = crop.ratings.select_related('buyer__user').all()
    avg_rating = ratings.aggregate(avg=Avg('stars'))['avg']
    avg_rating = round(avg_rating, 1) if avg_rating else None

    user_rating = None; has_enquiry = False; is_wishlisted = False; chat_room = None

    if request.user.is_authenticated and not request.user.is_anonymous:
        try:
            buyer         = request.user.buyer
            has_enquiry   = Enquiry.objects.filter(crop=crop, buyer=buyer).exists()
            user_rating   = Rating.objects.filter(crop=crop, buyer=buyer).first()
            is_wishlisted = Wishlist.objects.filter(crop=crop, buyer=buyer).exists()
            try: chat_room = ChatRoom.objects.get(crop=crop, buyer=buyer, farmer=crop.farmer)
            except: pass
        except: pass

    if request.method == 'POST' and request.user.is_authenticated:
        try:
            buyer = request.user.buyer
            form  = EnquiryForm(request.POST)
            if form.is_valid():
                e = form.save(commit=False); e.crop = crop; e.buyer = buyer; e.save()
                messages.success(request, "Enquiry sent! The farmer will contact you soon.")
            else:
                messages.error(request, "Please fill in all fields.")
        except:
            messages.error(request, "Only buyers can send enquiries.")
        return redirect(f'/crop/{pk}/')

    return render(request, 'market/crop_detail.html', {
        'crop': crop, 'related': related, 'form': EnquiryForm(),
        'ratings': ratings, 'avg_rating': avg_rating,
        'user_rating': user_rating, 'has_enquiry': has_enquiry,
        'is_wishlisted': is_wishlisted, 'chat_room': chat_room,
    })


# ── SUBMIT RATING ─────────────────────────────────────
@login_required
def submit_rating(request, crop_pk):
    if request.method != 'POST': return redirect(f'/crop/{crop_pk}/')
    try: buyer = request.user.buyer
    except: messages.error(request, "Only buyers can review."); return redirect(f'/crop/{crop_pk}/')
    crop = get_object_or_404(Crop, pk=crop_pk)
    if not Enquiry.objects.filter(crop=crop, buyer=buyer).exists():
        messages.error(request, "Enquire about this crop before reviewing.")
        return redirect(f'/crop/{crop_pk}/')
    stars = request.POST.get('stars', '')
    if not stars.isdigit() or not 1 <= int(stars) <= 5:
        messages.error(request, "Pick 1–5 stars."); return redirect(f'/crop/{crop_pk}/')
    Rating.objects.update_or_create(crop=crop, buyer=buyer,
        defaults={'stars': int(stars), 'review': request.POST.get('review', '').strip()})
    messages.success(request, "Review saved! ⭐")
    return redirect(f'/crop/{crop_pk}/')


# ── DELETE RATING ─────────────────────────────────────
@login_required
def delete_rating(request, crop_pk):
    try: Rating.objects.filter(crop_id=crop_pk, buyer=request.user.buyer).delete(); messages.success(request, "Review removed.")
    except: pass
    return redirect(f'/crop/{crop_pk}/')


# ── TOGGLE WISHLIST ───────────────────────────────────
@login_required
def toggle_wishlist(request, crop_pk):
    try: buyer = request.user.buyer
    except:
        if request.GET.get('fmt') == 'json': return JsonResponse({'error': 'buyers only'}, status=403)
        return redirect(f'/crop/{crop_pk}/')
    crop = get_object_or_404(Crop, pk=crop_pk)
    obj, created = Wishlist.objects.get_or_create(buyer=buyer, crop=crop)
    if not created: obj.delete(); action = 'removed'
    else: action = 'added'
    if request.GET.get('fmt') == 'json':
        return JsonResponse({'action': action, 'count': crop.wishlisted_by.count()})
    messages.success(request, f"{'Added to' if action == 'added' else 'Removed from'} wishlist.")
    return redirect(request.META.get('HTTP_REFERER', f'/crop/{crop_pk}/'))


# ── WISHLIST PAGE ─────────────────────────────────────
@login_required
def wishlist_view(request):
    try: buyer = request.user.buyer
    except: return redirect('/home/')
    items = Wishlist.objects.filter(buyer=buyer).select_related('crop', 'crop__farmer__user', 'crop__category')
    return render(request, 'market/wishlist.html', {'items': items, 'count': items.count()})


# ── FARMER DASHBOARD ─────────────────────────────────
@login_required
def farmer_dashboard(request):
    try: farmer = request.user.farmer
    except: return redirect('/home/')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_crop':
            form = CropForm(request.POST, request.FILES)
            if form.is_valid():
                crop = form.save(commit=False); crop.farmer = farmer; crop.save()
                messages.success(request, f"'{crop.name}' listed! 🌾")
            else:
                for f, e in form.errors.items(): messages.error(request, f"{f}: {e[0]}"); break
            return redirect('/farmer-dashboard/')

        elif action == 'delete_crop':
            try:
                c = Crop.objects.get(id=request.POST.get('crop_id'), farmer=farmer)
                n = c.name; c.delete(); messages.success(request, f"'{n}' removed.")
            except: messages.error(request, "Crop not found.")
            return redirect('/farmer-dashboard/')

        elif action == 'mark_read':
            try:
                e = Enquiry.objects.get(id=request.POST.get('enquiry_id'), crop__farmer=farmer)
                e.is_read = True; e.save(); messages.success(request, "Marked as read.")
            except: pass
            return redirect('/farmer-dashboard/')

        elif action == 'reply_enquiry':
            reply_msg = request.POST.get('reply_message', '').strip()
            if not reply_msg: messages.error(request, "Reply cannot be empty."); return redirect('/farmer-dashboard/')
            try:
                e = Enquiry.objects.get(id=request.POST.get('enquiry_id'), crop__farmer=farmer)
                e.is_read = True; e.save()
                EnquiryReply.objects.update_or_create(enquiry=e, defaults={'message': reply_msg})
                messages.success(request, "Reply sent! ✅")
            except: messages.error(request, "Enquiry not found.")
            return redirect('/farmer-dashboard/')

    crops       = Crop.objects.filter(farmer=farmer).select_related('category')
    enquiries   = Enquiry.objects.filter(crop__farmer=farmer).select_related('buyer__user', 'crop').order_by('-created')
    chats       = ChatRoom.objects.filter(farmer=farmer).select_related('buyer__user', 'crop').order_by('-created')
    all_ratings = Rating.objects.filter(crop__farmer=farmer)
    avg_rating  = all_ratings.aggregate(avg=Avg('stars'))['avg']
    avg_rating  = round(avg_rating, 1) if avg_rating else None
    recent_reviews = all_ratings.select_related('buyer__user', 'crop').order_by('-created')[:5]
    total_wishlist = Wishlist.objects.filter(crop__farmer=farmer).count()

    return render(request, 'market/farmer_dashboard.html', {
        'farmer'         : farmer,
        'crops'          : crops,
        'categories'     : Category.objects.all(),
        'enquiries'      : enquiries,
        'chats'          : chats,
        'crop_form'      : CropForm(),
        'total_crops'    : crops.count(),
        'available_crops': crops.filter(status='available').count(),
        'sold_crops'     : crops.filter(status='sold').count(),
        'total_enquiries': enquiries.count(),
        'unread'         : enquiries.filter(is_read=False).count(),
        'avg_farm_rating': avg_rating,
        'total_wishlist' : total_wishlist,
        'recent_reviews' : recent_reviews,
    })


# ── BUYER DASHBOARD ───────────────────────────────────
@login_required
def buyer_dashboard(request):
    try: buyer = request.user.buyer
    except: return redirect('/home/')

    enquiries      = Enquiry.objects.filter(buyer=buyer).select_related('crop__farmer__user', 'crop__category').prefetch_related('reply').order_by('-created')
    chat_rooms     = ChatRoom.objects.filter(buyer=buyer).select_related('farmer__user', 'crop').order_by('-created')
    wishlist_items = Wishlist.objects.filter(buyer=buyer).select_related('crop', 'crop__farmer__user')
    my_ratings     = Rating.objects.filter(buyer=buyer).select_related('crop')

    return render(request, 'market/buyer_dashboard.html', {
        'buyer'          : buyer,
        'enquiries'      : enquiries,
        'total_enquiries': enquiries.count(),
        'chat_rooms'     : chat_rooms,
        'wishlist_items' : wishlist_items,
        'wishlist_count' : wishlist_items.count(),
        'my_ratings'     : my_ratings,
    })


# ── EDIT PROFILE ─────────────────────────────────────
@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name  = request.POST.get('last_name', '').strip()
        user.email      = request.POST.get('email', '').strip()
        user.save()
        try:
            f = user.farmer
            f.phone = request.POST.get('phone', ''); f.district = request.POST.get('district', '')
            f.state = request.POST.get('state', '');  f.farm_id = request.POST.get('farm_id', '')
            f.specialty = request.POST.get('specialty', ''); f.bio = request.POST.get('bio', '')
            if request.FILES.get('photo'): f.photo = request.FILES['photo']
            f.save()
        except: pass
        try:
            b = user.buyer
            b.phone = request.POST.get('phone', ''); b.district = request.POST.get('district', '')
            b.state = request.POST.get('state', ''); b.delivery_address = request.POST.get('delivery_address', '')
            b.save()
        except: pass
        messages.success(request, "Profile updated successfully! ✅")
        return redirect('/edit-profile/')
    return render(request, 'market/edit_profile.html')


# ── EDIT CROP ─────────────────────────────────────────
@login_required
def edit_crop(request, pk):
    try: farmer = request.user.farmer
    except: return redirect('/home/')
    crop = get_object_or_404(Crop, pk=pk, farmer=farmer)
    if request.method == 'POST':
        form = CropForm(request.POST, request.FILES, instance=crop)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{crop.name}' updated! ✅")
            return redirect('/farmer-dashboard/')
        for f, e in form.errors.items(): messages.error(request, f"{f}: {e[0]}"); break
    else:
        form = CropForm(instance=crop)
    return render(request, 'market/edit_crop.html', {'crop': crop, 'form': form, 'categories': Category.objects.all()})


# ── CHAT ROOM ─────────────────────────────────────────
@login_required
def chat_room(request, room_id):
    try: room = ChatRoom.objects.select_related('farmer__user', 'buyer__user', 'crop').get(pk=room_id)
    except: return redirect('/home/')
    user = request.user
    is_farmer = hasattr(user, 'farmer') and user.farmer == room.farmer
    is_buyer  = hasattr(user, 'buyer')  and user.buyer  == room.buyer
    if not is_farmer and not is_buyer: return redirect('/home/')
    chat_messages = ChatMessage.objects.filter(room=room).select_related('sender').order_by('timestamp')
    return render(request, 'market/chat_room.html', {
        'room': room, 'chat_messages': chat_messages, 'user': user,
    })


# ── START CHAT ────────────────────────────────────────
@login_required
def start_chat(request, crop_pk):
    crop = get_object_or_404(Crop, pk=crop_pk)
    try: buyer = request.user.buyer
    except: messages.error(request, "Only buyers can start a chat."); return redirect(f'/crop/{crop_pk}/')
    room, _ = ChatRoom.objects.get_or_create(farmer=crop.farmer, buyer=buyer, crop=crop)
    return redirect(f'/chat/{room.pk}/')


# ── FARMER START CHAT ─────────────────────────────────
@login_required
def farmer_start_chat(request, enquiry_pk):
    try: farmer = request.user.farmer
    except: return redirect('/home/')
    enquiry = get_object_or_404(Enquiry, pk=enquiry_pk, crop__farmer=farmer)
    room, _ = ChatRoom.objects.get_or_create(farmer=farmer, buyer=enquiry.buyer, crop=enquiry.crop)
    return redirect(f'/chat/{room.pk}/')

@login_required
def place_order(request, crop_pk):
    crop = get_object_or_404(Crop, pk=crop_pk, status='available')
    try:
        buyer = request.user.buyer
    except:
        messages.error(request, "Only buyers can place orders.")
        return redirect(f'/crop/{crop_pk}/')

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        delivery = request.POST.get('delivery')
        payment  = request.POST.get('payment')
        address  = request.POST.get('address', '').strip()
        note     = request.POST.get('note', '').strip()

        if delivery not in ['pickup', 'delivery']:
            messages.error(request, "Choose a delivery option.")
            return redirect(f'/crop/{crop_pk}/')

        if payment not in ['cod', 'upi']:
            messages.error(request, "Choose a payment method.")
            return redirect(f'/crop/{crop_pk}/')

        if delivery == 'delivery' and not address:
            messages.error(request, "Please provide your delivery address.")
            return redirect(f'/order/place/{crop_pk}/')

        try:
            price = float(crop.price)
        except:
            price = 0

        order = Order.objects.create(
            crop=crop,
            buyer=buyer,
            farmer=crop.farmer,
            quantity=quantity,
            total_price=price * quantity,
            delivery=delivery,
            payment=payment,
            address=address,
            note=note,
        )
        messages.success(request, f"Order placed successfully! 🎉")
        return redirect(f'/order/{order.pk}/')

    return render(request, 'market/place_order.html', {'crop': crop})


@login_required
def order_detail(request, pk):
    try:
        buyer = request.user.buyer
        order = get_object_or_404(Order, pk=pk, buyer=buyer)
    except:
        try:
            farmer = request.user.farmer
            order  = get_object_or_404(Order, pk=pk, farmer=farmer)
        except:
            return redirect('/home/')
    return render(request, 'market/order_detail.html', {'order': order})


@login_required
def update_order_status(request, pk):
    try:
        farmer = request.user.farmer
        order  = get_object_or_404(Order, pk=pk, farmer=farmer)
    except:
        messages.error(request, "Only the farmer can update order status.")
        return redirect('/home/')
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['confirmed','dispatched','delivered','cancelled']:
            order.status = status
            order.save()
            messages.success(request, f"Order marked as {order.get_status_display()}.")
    return redirect(f'/order/{pk}/')


@login_required
def my_orders(request):
    try:
        buyer  = request.user.buyer
        orders = Order.objects.filter(buyer=buyer).select_related('crop','farmer__user')
        return render(request, 'market/my_orders.html', {'orders': orders})
    except:
        pass
    try:
        farmer = request.user.farmer
        orders = Order.objects.filter(farmer=farmer).select_related('crop','buyer__user')
        return render(request, 'market/my_orders.html', {'orders': orders, 'is_farmer': True})
    except:
        pass
    return redirect('/home/')