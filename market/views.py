from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .forms import RegisterForm, LoginForm, CropForm
from .models import Crop, Category, FarmerProfile, BuyerProfile, Rating, Order, Cart
from decimal import Decimal

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
    # FarmerProfile raises RelatedObjectDoesNotExist if user is not a farmer
    try: request.user.farmer; return redirect('/farmer-dashboard/')
    except Exception: pass
    # BuyerProfile raises RelatedObjectDoesNotExist if user is not a buyer
    try: request.user.buyer; return redirect('/buyer-dashboard/')
    except Exception: pass
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

    paginator = Paginator(crops, 6)
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

    user_rating         = None
    in_cart             = False
    has_delivered_order = False

    # hasattr check prevents AttributeError on AnonymousUser
    is_farmer = (
        request.user.is_authenticated and
        hasattr(request.user, 'farmer') and
        request.user.farmer == crop.farmer  # must be THIS crop's farmer
    )
    is_buyer = (
        request.user.is_authenticated and
        hasattr(request.user, 'buyer')
    )

    # only fetch buyer-specific data if user is a buyer
    # and not the farmer of this crop
    if is_buyer and not is_farmer:
        try:
            buyer               = request.user.buyer
            user_rating         = Rating.objects.filter(crop=crop, buyer=buyer).first()
            # buyer can only review after receiving the crop
            has_delivered_order = Order.objects.filter(crop=crop, buyer=buyer, status='delivered').exists()
            in_cart             = Cart.objects.filter(buyer=buyer, crop=crop).exists()
        except Exception as e:
            print(f"Crop detail buyer data error: {e}")

    return render(request, 'market/crop_detail.html', {
        'crop'               : crop,
        'related'            : related,
        'ratings'            : ratings,
        'avg_rating'         : avg_rating,
        'user_rating'        : user_rating,
        'in_cart'            : in_cart,
        'is_farmer'          : is_farmer,
        'is_buyer'           : is_buyer,
        'has_delivered_order': has_delivered_order,
    })


# ── SUBMIT RATING ─────────────────────────────────────
@login_required
def submit_rating(request, crop_pk):
    if request.method != 'POST': return redirect(f'/crop/{crop_pk}/')
    try: buyer = request.user.buyer
    except:
        messages.error(request, "Only buyers can review.")
        return redirect(f'/crop/{crop_pk}/')
    crop = get_object_or_404(Crop, pk=crop_pk)
    if not Order.objects.filter(crop=crop, buyer=buyer, status='delivered').exists():
        messages.error(request, "You can only review crops you have received.")
        return redirect(f'/crop/{crop_pk}/')
    stars = request.POST.get('stars', '')
    if not stars.isdigit() or not 1 <= int(stars) <= 5:
        messages.error(request, "Pick 1–5 stars.")
        return redirect(f'/crop/{crop_pk}/')
    Rating.objects.update_or_create(
        crop=crop, buyer=buyer,
        defaults={'stars': int(stars), 'review': request.POST.get('review', '').strip()}
    )
    messages.success(request, "Review saved! ⭐")
    return redirect(f'/crop/{crop_pk}/')


# ── DELETE RATING ─────────────────────────────────────
@login_required
def delete_rating(request, crop_pk):
    try: Rating.objects.filter(crop_id=crop_pk, buyer=request.user.buyer).delete()
    except Exception: pass
    messages.success(request, "Review removed.")
    return redirect(f'/crop/{crop_pk}/')


# ── FARMER DASHBOARD ─────────────────────────────────
@login_required
def farmer_dashboard(request):
    # redirect non-farmers away from farmer dashboard
    try: farmer = request.user.farmer
    except Exception: return redirect('/home/')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── ADD CROP ──
        if action == 'add_crop':
            form = CropForm(request.POST, request.FILES)
            if form.is_valid():
                crop = form.save(commit=False)
                crop.farmer = farmer
                crop.save()
                messages.success(request, f"'{crop.name}' listed! 🌾")
            else:
                for f, e in form.errors.items():
                    messages.error(request, f"{f}: {e[0]}"); break
            return redirect('/farmer-dashboard/?tab=crops')

        # ── DELETE CROP ──
        elif action == 'delete_crop':
            try:
                c = Crop.objects.get(id=request.POST.get('crop_id'), farmer=farmer)
                n = c.name
                c.delete()
                messages.success(request, f"'{n}' removed.")
            except:
                messages.error(request, "Crop not found.")
            return redirect('/farmer-dashboard/?tab=crops')

        # ── UPDATE ORDER ──
        elif action == 'update_order':
            order_id    = request.POST.get('order_id', '').strip()
            status      = request.POST.get('status', '').strip()
            farmer_note = request.POST.get('farmer_note', '').strip()
            try:
                o = Order.objects.get(id=order_id, farmer=farmer)

                if status == 'confirmed' and o.status == 'pending':
                    crop = o.crop
                    if o.quantity > crop.quantity:
                        messages.error(request, f"Only {crop.quantity} {crop.unit} available. Cannot confirm.")
                        return redirect('/farmer-dashboard/')
                    crop.quantity -= o.quantity
                    if crop.quantity == 0:
                        crop.status = 'sold'
                    crop.save()
                    o.status = 'confirmed'
                    o.farmer_seen = True

                elif status == 'dispatched' and o.status == 'confirmed':
                    o.status = 'dispatched'

                elif status == 'delivered' and o.status == 'dispatched':
                    o.status = 'delivered'

                elif status == 'cancelled' and o.status in ['pending', 'confirmed']:
                    if o.status == 'confirmed':
                        crop = o.crop
                        crop.quantity += o.quantity
                        if crop.status == 'sold':
                            crop.status = 'available'
                        crop.save()
                    o.status = 'cancelled'

                else:
                    messages.error(request, f"Cannot change from {o.get_status_display()} to {status}.")
                    return redirect('/farmer-dashboard/?tab=orders')

                if farmer_note:
                    o.farmer_note = farmer_note
                o.save()
                messages.success(request, f"Order #{o.pk} marked as {o.get_status_display()}. ✅")

            except Order.DoesNotExist:
                messages.error(request, "Order not found.")
            return redirect('/farmer-dashboard/?tab=orders')

    # ── GET ──
    crops          = Crop.objects.filter(farmer=farmer).select_related('category')
    orders         = Order.objects.filter(farmer=farmer).select_related('crop', 'buyer__user').order_by('-created_at')
    all_ratings    = Rating.objects.filter(crop__farmer=farmer)
    avg_rating     = all_ratings.aggregate(avg=Avg('stars'))['avg']
    avg_rating     = round(avg_rating, 1) if avg_rating else None
    recent_reviews = all_ratings.select_related('buyer__user', 'crop').order_by('-created')[:5]
    total_revenue  = Order.objects.filter(
        farmer=farmer, status='delivered'
    ).aggregate(total=Sum('total_price'))['total'] or 0
    orders_this_month = Order.objects.filter(
        farmer=farmer,
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year,
    ).count()
    top_crop = Order.objects.filter(
        farmer=farmer
    ).values('crop__name').annotate(count=Count('id')).order_by('-count').first()

    return render(request, 'market/farmer_dashboard.html', {
        'farmer'            : farmer,
        'crops'             : crops,
        'categories'        : Category.objects.all(),
        'crop_form'         : CropForm(),
        'total_crops'       : crops.count(),
        'available_crops'   : crops.filter(status='available').count(),
        'sold_crops'        : crops.filter(status='sold').count(),
        'avg_farm_rating'   : avg_rating,
        'recent_reviews'    : recent_reviews,
        'orders'            : orders,
        'order_count'       : orders.count(),
        'pending_orders'    : orders.filter(status='pending').count(),
        'total_revenue'     : total_revenue,
        'orders_this_month' : orders_this_month,
        'top_crop'          : top_crop,
    })


# ── BUYER DASHBOARD ───────────────────────────────────
@login_required
def buyer_dashboard(request):
    # redirect non-buyers away from buyer dashboard
    try: buyer = request.user.buyer
    except Exception: return redirect('/home/')

    orders = Order.objects.filter(buyer=buyer).select_related(
        'crop', 'crop__category', 'crop__farmer__user', 'farmer__user'
    ).order_by('-created_at')
    my_ratings      = Rating.objects.filter(buyer=buyer).select_related('crop', 'crop__farmer__user')
    active_orders   = orders.filter(status__in=['pending', 'confirmed', 'dispatched']).count()
    delivered_count = orders.filter(status='delivered').count()

    return render(request, 'market/buyer_dashboard.html', {
        'buyer'          : buyer,
        'orders'         : orders,
        'order_count'    : orders.count(),
        'active_orders'  : active_orders,
        'delivered_count': delivered_count,
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
            f.phone     = request.POST.get('phone', '')
            f.district  = request.POST.get('district', '')
            f.state     = request.POST.get('state', '')
            f.farm_id   = request.POST.get('farm_id', '')
            f.specialty = request.POST.get('specialty', '')
            f.bio       = request.POST.get('bio', '')
            f.upi_id    = request.POST.get('upi_id', '')
            if request.FILES.get('photo'): f.photo = request.FILES['photo']
            f.save()
        except Exception:
            # user is not a farmer, skip farmer profile update
            pass
        try:
            b = user.buyer
            b.phone            = request.POST.get('phone', '')
            b.district         = request.POST.get('district', '')
            b.state            = request.POST.get('state', '')
            b.delivery_address = request.POST.get('delivery_address', '')
            b.save()
        except Exception:
            # user is not a buyer, skip buyer profile update
            pass

        messages.success(request, "Profile updated successfully! ✅")
        return redirect('/edit-profile/')
    return render(request, 'market/edit_profile.html')


# ── EDIT CROP ─────────────────────────────────────────
@login_required
def edit_crop(request, pk):
    try: farmer = request.user.farmer
    except Exception: return redirect('/home/')
    crop = get_object_or_404(Crop, pk=pk, farmer=farmer)
    if request.method == 'POST':
        form = CropForm(request.POST, request.FILES, instance=crop)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{crop.name}' updated! ✅")
            return redirect('/farmer-dashboard/')
        for f, e in form.errors.items():
            messages.error(request, f"{f}: {e[0]}"); break
    else:
        form = CropForm(instance=crop)
    return render(request, 'market/edit_crop.html', {
        'crop': crop, 'form': form, 'categories': Category.objects.all()
    })


# ── ORDER DETAIL ─────────────────────────────────────
@login_required
def order_detail(request, pk):
    is_farmer = False
    try:
        buyer = request.user.buyer
        order = get_object_or_404(Order, pk=pk, buyer=buyer)
        if order.status in ['confirmed', 'dispatched'] and not order.buyer_seen:
            order.buyer_seen = True
            order.save()
    except Exception:
        try:
            farmer    = request.user.farmer
            order     = get_object_or_404(Order, pk=pk, farmer=farmer)
            is_farmer = True
            if order.status == 'pending' and not order.farmer_seen:
                order.farmer_seen = True
                order.save()
        except Exception:
            return redirect('/home/')

    steps = [
        ('pending',    'Pending',    '⏳'),
        ('confirmed',  'Confirmed',  '✅'),
        ('dispatched', 'Dispatched', '🚚'),
        ('delivered',  'Delivered',  '🎉'),
    ]
    status_order = ['pending', 'confirmed', 'dispatched', 'delivered']
    step_index   = status_order.index(order.status) + 1 if order.status in status_order else 0

    return render(request, 'market/order_detail.html', {
        'order'     : order,
        'is_farmer' : is_farmer,
        'steps'     : steps,
        'step_index': step_index,
    })


# ── UPDATE ORDER STATUS ──────────────────────────────
@login_required
def update_order_status(request, pk):
    if request.method != 'POST':
        return redirect(f'/order/{pk}/')

    order       = get_object_or_404(Order, pk=pk)
    status      = request.POST.get('status', '').strip()
    farmer_note = request.POST.get('farmer_note', '').strip()

    # ── FARMER BLOCK ──
    # AttributeError raised if user has no farmer profile
    # meaning user is a buyer — fall through to buyer block
    try:
        farmer = request.user.farmer

        # security check — farmer can only update their own orders
        if order.farmer != farmer:
            messages.error(request, "Not your order.")
            return redirect(f'/order/{pk}/')

        # stock deducted ONLY on confirm — not at cart or checkout
        if status == 'confirmed' and order.status == 'pending':
            crop = order.crop
            if order.quantity > crop.quantity:
                messages.error(request, f"Only {crop.quantity} {crop.unit} available.")
                return redirect(f'/order/{pk}/')
            crop.quantity -= order.quantity
            if crop.quantity == 0:
                crop.status = 'sold'
            crop.save()
            order.status = 'confirmed'
            order.farmer_seen = True

        # strict status progression — cannot skip steps
        elif status == 'dispatched' and order.status == 'confirmed':
            order.status = 'dispatched'

        elif status == 'delivered' and order.status == 'dispatched':
            order.status = 'delivered'

        # stock restored if farmer cancels a confirmed order
        elif status == 'cancelled' and order.status in ['pending', 'confirmed']:
            if order.status == 'confirmed':
                crop = order.crop
                crop.quantity += order.quantity
                if crop.status == 'sold':
                    crop.status = 'available'
                crop.save()
            order.status = 'cancelled'

        else:
            messages.error(request, f"Cannot change from {order.get_status_display()} to {status}.")
            return redirect(f'/order/{pk}/')

        if farmer_note:
            order.farmer_note = farmer_note
        order.save()
        messages.success(request, f"Order marked as {order.get_status_display()}. ✅")
        return redirect(f'/order/{pk}/')

    except AttributeError:
        # user has no farmer profile, check if buyer
        pass

    # ── BUYER BLOCK ──
    # buyer can only cancel pending orders within 1 hour
    try:
        buyer = request.user.buyer

        # security check — buyer can only cancel their own orders
        if order.buyer != buyer:
            messages.error(request, "Not your order.")
            return redirect(f'/order/{pk}/')

        if status == 'cancelled':
            if order.status != 'pending':
                messages.error(request, "You can only cancel pending orders.")
                return redirect(f'/order/{pk}/')
            # 1 hour cancellation window
            time_limit = order.created_at + timedelta(hours=1)
            if timezone.now() > time_limit:
                messages.error(request, "Cannot cancel after 1 hour of placing order.")
                return redirect(f'/order/{pk}/')
            order.status = 'cancelled'
            order.save()
            messages.success(request, "Order cancelled successfully.")
        return redirect(f'/order/{pk}/')

    except AttributeError:
        pass

    return redirect('/home/')


# ── MY ORDERS ─────────────────────────────────────────
@login_required
def my_orders(request):
    try:
        buyer  = request.user.buyer
        orders = Order.objects.filter(buyer=buyer).select_related('crop', 'farmer__user')
        return render(request, 'market/my_orders.html', {'orders': orders})
    except Exception: pass
    try:
        farmer = request.user.farmer
        orders = Order.objects.filter(farmer=farmer).select_related('crop', 'buyer__user')
        return render(request, 'market/my_orders.html', {'orders': orders, 'is_farmer': True})
    except Exception: pass
    return redirect('/home/')


# ── CART ADD ─────────────────────────────────────────
@login_required
def cart_add(request, crop_pk):
    crop = get_object_or_404(Crop, pk=crop_pk, status='available')
    try: buyer = request.user.buyer
    except Exception:
        messages.error(request, "Only buyers can add to cart.")
        return redirect(f'/crop/{crop_pk}/')

    if crop.quantity < 1:
        messages.error(request, f"'{crop.name}' is out of stock.")
        return redirect(f'/crop/{crop_pk}/')

    cart_item, created = Cart.objects.get_or_create(buyer=buyer, crop=crop)
    if created:
        messages.success(request, f"'{crop.name}' added to cart! 🛒")
    else:
        messages.info(request, f"'{crop.name}' is already in your cart.")
    return redirect(request.META.get('HTTP_REFERER', f'/crop/{crop_pk}/'))


# ── CART REMOVE ──────────────────────────────────────
@login_required
def cart_remove(request, crop_pk):
    try:
        buyer = request.user.buyer
        Cart.objects.filter(buyer=buyer, crop_id=crop_pk).delete()
        messages.success(request, "Removed from cart.")
    except Exception as e:
        messages.error(request, "Could not remove item from cart.")
        print(f"Cart remove error: {e}")
    return redirect('/cart/')


# ── CART UPDATE ──────────────────────────────────────
@login_required
def cart_update(request, crop_pk):
    if request.method == 'POST':
        try:
            buyer = request.user.buyer
            qty   = int(request.POST.get('quantity', 1))
            if qty < 1: qty = 1
            Cart.objects.filter(buyer=buyer, crop_id=crop_pk).update(quantity=qty)
        except Exception as e:
            print(f"Cart update error: {e}")
    return redirect('/cart/')


# ── CART VIEW ────────────────────────────────────────
@login_required
def cart_view(request):
    try: buyer = request.user.buyer
    except Exception: return redirect('/home/')
    items = Cart.objects.filter(buyer=buyer).select_related('crop__category', 'crop__farmer__user')
    total = sum(item.subtotal for item in items)
    return render(request, 'market/cart.html', {
        'items': items, 'total': total, 'count': items.count()
    })


# ── CART CHECKOUT ────────────────────────────────────
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

        # validate stock
        for item in items:
            if item.quantity > item.crop.quantity:
                messages.error(request, f"Only {item.crop.quantity} {item.crop.unit} available for '{item.crop.name}'.")
                return redirect('/cart/')

        # create orders — stock deducted only when farmer confirms
        placed = []
        for item in items:
            price = item.crop.price
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
        # store order IDs in session to show on success page
        request.session['last_order_ids'] = [o.pk for o in placed]
        return redirect('/order/success/')

    return render(request, 'market/checkout.html', {'items': items, 'total': total})

# ── ORDER SUCCESS ─────────────────────────────────────
@login_required
def order_success(request):
    try: buyer = request.user.buyer
    except Exception: return redirect('/home/')

    # retrieve order IDs stored in session during checkout
    # session.pop removes them after reading — prevents refresh issues
    order_ids = request.session.pop('last_order_ids', [])
    orders    = Order.objects.filter(
        pk__in=order_ids
    ).select_related('crop', 'crop__category', 'farmer__user')

    if not orders.exists():
        return redirect('/orders/')

    total = sum(o.total_price for o in orders)

    return render(request, 'market/order_success.html', {
        'orders': orders,
        'total' : total,
    })