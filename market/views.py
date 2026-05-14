from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Avg
from .forms import RegisterForm, LoginForm, CropForm
from .models import Crop, Category, FarmerProfile, BuyerProfile, Rating, Order, Cart


# ── HOME ─────────────────────────────────────────────
def home(request):
    featured_crops = Crop.objects.filter(is_featured=True, status='available').select_related('farmer__user', 'category')
    all_crops      = Crop.objects.filter(status='available').select_related('farmer__user', 'category')
    categories     = Category.objects.all()
    total_crops    = Crop.objects.filter(status='available').count()
    total_farmers  = FarmerProfile.objects.count()
    total_buyers   = BuyerProfile.objects.count()
    raw_districts  = Crop.objects.filter(status='available').values_list('district', flat=True)
    districts      = sorted(set(d.strip() for d in raw_districts if d.strip()))

    return render(request, 'market/home.html', {
        'featured_crops': featured_crops,
        'all_crops'     : all_crops,
        'categories'    : categories,
        'total_crops'   : total_crops,
        'total_farmers' : total_farmers,
        'total_buyers'  : total_buyers,
        'districts'     : districts,
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
    crop       = get_object_or_404(Crop.objects.select_related('farmer__user', 'category'), pk=pk)
    related    = Crop.objects.filter(category=crop.category, status='available').exclude(pk=pk).select_related('farmer__user')[:4]
    ratings    = crop.ratings.select_related('buyer__user').all()
    avg_rating = ratings.aggregate(avg=Avg('stars'))['avg']
    avg_rating = round(avg_rating, 1) if avg_rating else None
    user_rating = None
    in_cart     = False

    if request.user.is_authenticated:
        try:
            buyer       = request.user.buyer
            user_rating = Rating.objects.filter(crop=crop, buyer=buyer).first()
            in_cart     = Cart.objects.filter(buyer=buyer, crop=crop).exists()
        except: pass

    return render(request, 'market/crop_detail.html', {
        'crop'       : crop,
        'related'    : related,
        'ratings'    : ratings,
        'avg_rating' : avg_rating,
        'user_rating': user_rating,
        'in_cart'    : in_cart,
    })


# ── SUBMIT RATING ─────────────────────────────────────
@login_required
def submit_rating(request, crop_pk):
    if request.method != 'POST': return redirect(f'/crop/{crop_pk}/')
    try: buyer = request.user.buyer
    except: messages.error(request, "Only buyers can review."); return redirect(f'/crop/{crop_pk}/')
    crop = get_object_or_404(Crop, pk=crop_pk)
    # only buyers who have a delivered order can review
    has_order = Order.objects.filter(crop=crop, buyer=buyer, status='delivered').exists()
    if not has_order:
        messages.error(request, "You can only review crops you have received.")
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

        elif action == 'update_order':
            order_id = request.POST.get('order_id')
            status   = request.POST.get('status')
            note     = request.POST.get('farmer_note', '').strip()
            try:
                o = Order.objects.get(id=order_id, farmer=farmer)
                if status in ['confirmed', 'dispatched', 'delivered', 'cancelled']:
                    o.status = status
                if note: o.farmer_note = note
                o.save()
                messages.success(request, f"Order #{o.pk} marked as {o.get_status_display()}.")
            except: messages.error(request, "Order not found.")
            return redirect('/farmer-dashboard/')

    crops          = Crop.objects.filter(farmer=farmer).select_related('category')
    orders         = Order.objects.filter(farmer=farmer).select_related('crop', 'buyer__user').order_by('-created_at')
    all_ratings    = Rating.objects.filter(crop__farmer=farmer)
    avg_rating     = all_ratings.aggregate(avg=Avg('stars'))['avg']
    avg_rating     = round(avg_rating, 1) if avg_rating else None
    recent_reviews = all_ratings.select_related('buyer__user', 'crop').order_by('-created')[:5]

    return render(request, 'market/farmer_dashboard.html', {
        'farmer'         : farmer,
        'crops'          : crops,
        'categories'     : Category.objects.all(),
        'crop_form'      : CropForm(),
        'total_crops'    : crops.count(),
        'available_crops': crops.filter(status='available').count(),
        'sold_crops'     : crops.filter(status='sold').count(),
        'avg_farm_rating': avg_rating,
        'recent_reviews' : recent_reviews,
        'orders'         : orders,
        'order_count'    : orders.count(),
        'pending_orders' : orders.filter(status='pending').count(),
    })


# ── BUYER DASHBOARD ───────────────────────────────────
@login_required
def buyer_dashboard(request):
    try: buyer = request.user.buyer
    except: return redirect('/home/')

    orders     = Order.objects.filter(buyer=buyer).select_related('crop', 'farmer__user').order_by('-created_at')
    my_ratings = Rating.objects.filter(buyer=buyer).select_related('crop')

    return render(request, 'market/buyer_dashboard.html', {
        'buyer'      : buyer,
        'orders'     : orders,
        'order_count': orders.count(),
        'my_ratings' : my_ratings,
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
            f.phone    = request.POST.get('phone', '')
            f.district = request.POST.get('district', '')
            f.state    = request.POST.get('state', '')
            f.farm_id  = request.POST.get('farm_id', '')
            f.specialty = request.POST.get('specialty', '')
            f.bio      = request.POST.get('bio', '')
            f.upi_id   = request.POST.get('upi_id', '')
            if request.FILES.get('photo'): f.photo = request.FILES['photo']
            f.save()
        except: pass
        try:
            b = user.buyer
            b.phone            = request.POST.get('phone', '')
            b.district         = request.POST.get('district', '')
            b.state            = request.POST.get('state', '')
            b.delivery_address = request.POST.get('delivery_address', '')
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


# ── ORDER DETAIL ─────────────────────────────────────
@login_required
def order_detail(request, pk):
    is_farmer = False
    try:
        buyer = request.user.buyer
        order = get_object_or_404(Order, pk=pk, buyer=buyer)
    except:
        try:
            farmer    = request.user.farmer
            order     = get_object_or_404(Order, pk=pk, farmer=farmer)
            is_farmer = True
        except:
            return redirect('/home/')

    steps = [
        ('pending',   'Pending',   '⏳'),
        ('confirmed', 'Confirmed', '✅'),
        ('dispatched','Dispatched','🚚'),
        ('delivered', 'Delivered', '🎉'),
    ]
    status_order = ['pending', 'confirmed', 'dispatched', 'delivered']
    step_index   = status_order.index(order.status) + 1 if order.status in status_order else 0

    return render(request, 'market/order_detail.html', {
        'order'     : order,
        'is_farmer' : is_farmer,
        'steps'     : steps,
        'step_index': step_index,
    })


# ── UPDATE ORDER STATUS ───────────────────────────────
@login_required
def update_order_status(request, pk):
    if request.method != 'POST': return redirect(f'/order/{pk}/')
    try:
        farmer = request.user.farmer
        order  = get_object_or_404(Order, pk=pk, farmer=farmer)
    except:
        # allow buyer to cancel
        try:
            buyer = request.user.buyer
            order = get_object_or_404(Order, pk=pk, buyer=buyer)
            if request.POST.get('status') == 'cancelled' and order.status == 'pending':
                order.status = 'cancelled'
                order.save()
                messages.success(request, "Order cancelled.")
        except: pass
        return redirect(f'/order/{pk}/')

    status      = request.POST.get('status')
    farmer_note = request.POST.get('farmer_note', '').strip()
    if status in ['confirmed', 'dispatched', 'delivered', 'cancelled']:
        order.status = status
    if farmer_note:
        order.farmer_note = farmer_note
    order.save()
    messages.success(request, f"Order marked as {order.get_status_display()}.")
    return redirect(f'/order/{pk}/')


# ── MY ORDERS ─────────────────────────────────────────
@login_required
def my_orders(request):
    try:
        buyer  = request.user.buyer
        orders = Order.objects.filter(buyer=buyer).select_related('crop', 'farmer__user')
        return render(request, 'market/my_orders.html', {'orders': orders})
    except: pass
    try:
        farmer = request.user.farmer
        orders = Order.objects.filter(farmer=farmer).select_related('crop', 'buyer__user')
        return render(request, 'market/my_orders.html', {'orders': orders, 'is_farmer': True})
    except: pass
    return redirect('/home/')


# ── CART ─────────────────────────────────────────────
@login_required
def cart_add(request, crop_pk):
    crop = get_object_or_404(Crop, pk=crop_pk, status='available')
    try: buyer = request.user.buyer
    except:
        messages.error(request, "Only buyers can add to cart.")
        return redirect(f'/crop/{crop_pk}/')
    cart_item, created = Cart.objects.get_or_create(buyer=buyer, crop=crop)
    if created:
        messages.success(request, f"'{crop.name}' added to cart! 🛒")
    else:
        messages.info(request, f"'{crop.name}' is already in your cart.")
    return redirect(request.META.get('HTTP_REFERER', f'/crop/{crop_pk}/'))


@login_required
def cart_remove(request, crop_pk):
    try:
        buyer = request.user.buyer
        Cart.objects.filter(buyer=buyer, crop_id=crop_pk).delete()
        messages.success(request, "Removed from cart.")
    except: pass
    return redirect('/cart/')


@login_required
def cart_update(request, crop_pk):
    if request.method == 'POST':
        try:
            buyer = request.user.buyer
            qty   = int(request.POST.get('quantity', 1))
            if qty < 1: qty = 1
            Cart.objects.filter(buyer=buyer, crop_id=crop_pk).update(quantity=qty)
        except: pass
    return redirect('/cart/')


@login_required
def cart_view(request):
    try: buyer = request.user.buyer
    except: return redirect('/home/')
    items = Cart.objects.filter(buyer=buyer).select_related('crop__category', 'crop__farmer__user')
    total = sum(item.subtotal for item in items)
    return render(request, 'market/cart.html', {'items': items, 'total': total, 'count': items.count()})


@login_required
def cart_checkout(request):
    try: buyer = request.user.buyer
    except: return redirect('/home/')

    items = Cart.objects.filter(buyer=buyer).select_related('crop__category', 'crop__farmer__user')
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('/cart/')

    total = sum(item.subtotal for item in items)

    if request.method == 'POST':
        delivery = request.POST.get('delivery')
        payment  = request.POST.get('payment')
        address  = request.POST.get('address', '').strip()
        note     = request.POST.get('note', '').strip()

        if delivery == 'delivery' and not address:
            messages.error(request, "Please provide your delivery address.")
            return redirect('/cart/checkout/')

        placed = []
        for item in items:
            try: price = float(item.crop.price)
            except: price = 0
            order = Order.objects.create(
                crop        = item.crop,
                buyer       = buyer,
                farmer      = item.crop.farmer,
                quantity    = item.quantity,
                total_price = price * item.quantity,
                delivery    = delivery,
                payment     = payment,
                address     = address,
                note        = note,
            )
            placed.append(order)

        items.delete()
        messages.success(request, f"{len(placed)} order(s) placed successfully! 🎉")
        return redirect('/orders/')

    return render(request, 'market/checkout.html', {'items': items, 'total': total})