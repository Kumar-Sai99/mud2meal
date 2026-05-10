from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Crop, Category, FarmerProfile, BuyerProfile, Enquiry, EnquiryReply
from django.contrib import messages
from django.core.paginator import Paginator


# ── HOME ─────────────────────────────────────────────
def home(request):
    featured_crops = Crop.objects.filter(is_featured=True, status='available')
    categories  = Category.objects.all()
    total_crops = Crop.objects.filter(status='available').count()
    all_crops      = Crop.objects.filter(status='available')

    
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
        'is_farmer'     : is_farmer,
    })

# ── REGISTER ─────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('/home/')

    if request.method == 'POST':
        username   = request.POST['username']
        email      = request.POST['email']
        first_name = request.POST['first_name']
        last_name  = request.POST['last_name']
        password1  = request.POST['password1']
        password2  = request.POST['password2']
        phone      = request.POST['phone']
        district   = request.POST['district']
        state      = request.POST['state']
        role       = request.POST['role']

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('/register/')


        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('/register/')


        user = User.objects.create_user(
            username=username, email=email,
            password=password1,
            first_name=first_name, last_name=last_name
        )

        if role == 'farmer':
            FarmerProfile.objects.create(
                user=user, phone=phone,
                district=district, state=state
            )
        else:
            BuyerProfile.objects.create(
                user=user, phone=phone,
                district=district, state=state
            )

        login(request, user)
        return redirect('/home/')

    return render(request, 'market/register.html')


# ── LOGIN ─────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/home/')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user     = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/home/')
        else:
            messages.error(request, 'Invalid username or password!')
            return redirect('/login/')

    return render(request, 'market/login.html')


# ── LOGOUT ───────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('/home/')


# ── DASHBOARD ROUTER ─────────────────────────────────
@login_required
def dashboard(request):
    try:
        request.user.farmer
        return redirect('/farmer-dashboard/')
    except:
        pass
    try:
        request.user.buyer
        return redirect('/buyer-dashboard/')
    except:
        pass
    return redirect('/home/')


# ── CROP LIST ────────────────────────────────────────
def crop_list(request):
    query    = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    district = request.GET.get('district', '')

    crops = Crop.objects.filter(status='available')

    if query:
        crops = crops.filter(name__icontains=query)
    if category:
        crops = crops.filter(category__id=category)
    if district:
        crops = crops.filter(district__icontains=district)

    paginator = Paginator(crops, 8)
    page      = request.GET.get('page', 1)
    crops     = paginator.get_page(page) 

    categories = Category.objects.all()
    raw_districts = Crop.objects.filter(status='available').values_list('district', flat=True)
    districts = sorted(set(d.strip() for d in raw_districts if d.strip()))

    return render(request, 'market/crop_list.html', {
        'crops'     : crops,
        'categories': categories,
        'districts' : districts,
        'query'     : query,
        'category'  : category,
        'district'  : district,
    })


# ── CROP DETAIL ──────────────────────────────────────
def crop_detail(request, pk):
    crop    = get_object_or_404(Crop, pk=pk)
    related = Crop.objects.filter(
        category=crop.category, status='available'
    ).exclude(pk=pk)[:4]
    success = False
    error   = None

    if request.method == 'POST' and request.user.is_authenticated:
        try:
            buyer   = request.user.buyer
            message = request.POST['message']
            phone   = request.POST['phone']
            Enquiry.objects.create(
                crop=crop, buyer=buyer,
                message=message, phone=phone
            )
            messages.success(request, "Enquiry sent! Farmer will contact you soon.")
            return redirect(f'/crop/{pk}/')
        except:
            messages.error(request, "Only buyers can send enquiries!")
            return redirect(f'/crop/{pk}/')

    return render(request, 'market/crop_detail.html', {
        'crop'   : crop,
        'related': related,
    })


# ── FARMER DASHBOARD ─────────────────────────────────
@login_required
def farmer_dashboard(request):
    try:
        farmer = request.user.farmer
    except:
        return redirect('/home/')

    success = None

    if request.method == 'POST':
        action = request.POST.get('action')

        # ADD CROP
        if action == 'add_crop':
            name        = request.POST.get('name')
            price       = request.POST.get('price')
            unit        = request.POST.get('unit', 'kg')
            quantity    = request.POST.get('quantity', '')
            description = request.POST.get('description', '')
            district    = request.POST.get('district', '')
            state       = request.POST.get('state', '')
            status      = request.POST.get('status', 'available')
            is_featured = request.POST.get('is_featured') == '1'
            category_id = request.POST.get('category')
            photo       = request.FILES.get('photo')

            crop = Crop(
                farmer=farmer, name=name,
                price=price, unit=unit,
                quantity=quantity, description=description,
                district=district, state=state,
                status=status, is_featured=is_featured,
            )
            if category_id:
                crop.category = Category.objects.get(id=category_id)
            if photo:
                crop.photo = photo
            crop.save()
            messages.success(request, f"'{name}' added successfully!")
            return redirect('/farmer-dashboard/')

        # DELETE CROP
        elif action == 'delete_crop':
            crop_id = request.POST.get('crop_id')
            try:
                crop = Crop.objects.get(id=crop_id, farmer=farmer)
                name = crop.name
                crop.delete()
                messages.success(request, f"'{name}' deleted!")
                return redirect('/farmer-dashboard/')
            except:
                pass

        # MARK ENQUIRY READ
        elif action == 'mark_read':
            enquiry_id = request.POST.get('enquiry_id')
            try:
                enquiry         = Enquiry.objects.get(id=enquiry_id, crop__farmer=farmer)
                enquiry.is_read = True
                enquiry.save()
                messages.success(request, "Enquiry marked as read!")
                return redirect('/farmer-dashboard/')
            except:
                pass

        # REPLY TO ENQUIRY
        elif action == 'reply_enquiry':
            enquiry_id  = request.POST.get('enquiry_id')
            reply_msg   = request.POST.get('reply_message')
            try:
                enquiry         = Enquiry.objects.get(id=enquiry_id, crop__farmer=farmer)
                enquiry.is_read = True
                enquiry.save()
                EnquiryReply.objects.update_or_create(
                    enquiry=enquiry,
                    defaults={'message': reply_msg}
                )
                messages.success(request, "Reply sent to buyer!")
                return redirect('/farmer-dashboard/')
            except:
                pass

    crops           = Crop.objects.filter(farmer=farmer)
    categories      = Category.objects.all()
    enquiries       = Enquiry.objects.filter(crop__farmer=farmer).order_by('-created')
    total_crops     = crops.count()
    available_crops = crops.filter(status='available').count()
    sold_crops      = crops.filter(status='sold').count()
    total_enquiries = enquiries.count()
    unread          = enquiries.filter(is_read=False).count()

    return render(request, 'market/farmer_dashboard.html', {
        'farmer'         : farmer,
        'crops'          : crops,
        'categories'     : categories,
        'enquiries'      : enquiries,
        'total_crops'    : total_crops,
        'available_crops': available_crops,
        'sold_crops'     : sold_crops,
        'total_enquiries': total_enquiries,
        'unread'         : unread,
        'success'        : success,
    })


# ── BUYER DASHBOARD ───────────────────────────────────
@login_required
def buyer_dashboard(request):
    try:
        buyer = request.user.buyer
    except:
        return redirect('/home/')

    enquiries       = Enquiry.objects.filter(buyer=buyer).order_by('-created')
    total_enquiries = enquiries.count()

    return render(request, 'market/buyer_dashboard.html', {
        'buyer'          : buyer,
        'enquiries'      : enquiries,
        'total_enquiries': total_enquiries,
    })


# ── EDIT PROFILE ─────────────────────────────────────
@login_required
def edit_profile(request):
    success = None

    if request.method == 'POST':
        user            = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name  = request.POST.get('last_name', '')
        user.email      = request.POST.get('email', '')
        user.save()

        # farmer profile
        try:
            farmer          = user.farmer
            farmer.phone    = request.POST.get('phone', '')
            farmer.district = request.POST.get('district', '')
            farmer.state    = request.POST.get('state', '')
            farmer.farm_id  = request.POST.get('farm_id', '')
            farmer.specialty = request.POST.get('specialty', '')
            farmer.bio      = request.POST.get('bio', '')
            farmer.save()
        except:
            pass

        # buyer profile
        try:
            buyer                  = user.buyer
            buyer.phone            = request.POST.get('phone', '')
            buyer.district         = request.POST.get('district', '')
            buyer.state            = request.POST.get('state', '')
            buyer.delivery_address = request.POST.get('delivery_address', '')
            buyer.save()
        except:
            pass

        messages.success(request, "Profile updated successfully!")
        return redirect('/edit-profile/')

    return render(request, 'market/edit_profile.html', {'success': success})

@login_required
def edit_crop(request, pk):
    try:
        farmer = request.user.farmer
    except:
        return redirect('/home/')

    crop = get_object_or_404(Crop, pk=pk, farmer=farmer)

    if request.method == 'POST':
        crop.name        = request.POST.get('name', crop.name)
        crop.price       = request.POST.get('price', crop.price)
        crop.unit        = request.POST.get('unit', crop.unit)
        crop.quantity    = request.POST.get('quantity', crop.quantity)
        crop.description = request.POST.get('description', crop.description)
        crop.district    = request.POST.get('district', crop.district)
        crop.state       = request.POST.get('state', crop.state)
        crop.status      = request.POST.get('status', crop.status)
        crop.is_featured = request.POST.get('is_featured') == '1'

        category_id = request.POST.get('category')
        if category_id:
            crop.category = Category.objects.get(id=category_id)

        photo = request.FILES.get('photo')
        if photo:
            crop.photo = photo

        crop.save()
        return redirect('/farmer-dashboard/')

    categories = Category.objects.all()
    return render(request, 'market/edit_crop.html', {
        'crop'      : crop,
        'categories': categories,
    })