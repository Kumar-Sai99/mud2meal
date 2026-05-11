from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Crop, Category, FarmerProfile, BuyerProfile, Enquiry, EnquiryReply
from .forms import RegisterForm, LoginForm, CropForm, EnquiryForm, FarmerProfileForm, BuyerProfileForm
from .models import ChatRoom


# ── HOME ─────────────────────────────────────────────
def home(request):
    featured_crops = Crop.objects.filter(
        is_featured=True, status='available'
    ).select_related('farmer__user', 'category')

    all_crops = Crop.objects.filter(
        status='available'
    ).select_related('farmer__user', 'category')

    categories  = Category.objects.all()
    total_crops = Crop.objects.filter(status='available').count()

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
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username   = data['username'],
                email      = data['email'],
                password   = data['password1'],
                first_name = data['first_name'],
                last_name  = data['last_name'],
            )
            if data['role'] == 'farmer':
                FarmerProfile.objects.create(
                    user     = user,
                    phone    = data['phone'],
                    district = data['district'],
                    state    = data['state'],
                )
            else:
                BuyerProfile.objects.create(
                    user     = user,
                    phone    = data['phone'],
                    district = data['district'],
                    state    = data['state'],
                )
            login(request, user)
            messages.success(request, f"Welcome {user.first_name}! Account created successfully!")
            return redirect('/home/')
        else:
            # show first error to user
            for field, errors in form.errors.items():
                messages.error(request, errors[0])
                break
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
            data = form.cleaned_data
            user = authenticate(
                request,
                username = data['username'],
                password = data['password'],
            )
            if user is not None:
                login(request, user)
                return redirect('/home/')
            else:
                messages.error(request, 'Invalid username or password!')
        else:
            messages.error(request, 'Please fill in all fields!')
    else:
        form = LoginForm()

    return render(request, 'market/login.html', {'form': form})


# ── LOGOUT ───────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('/home/')


# ── ROLE SELECT ──────────────────────────────────────
def role_select(request):
    if request.user.is_authenticated:
        return redirect('/home/')
    return render(request, 'market/role_select.html')


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

    crops = Crop.objects.filter(
        status='available'
    ).select_related('farmer__user', 'category')

    if query:
        crops = crops.filter(name__icontains=query)
    if category:
        crops = crops.filter(category__id=category)
    if district:
        crops = crops.filter(district__icontains=district)

    paginator = Paginator(crops, 8)
    page      = request.GET.get('page', 1)
    crops     = paginator.get_page(page)

    categories    = Category.objects.all()
    raw_districts = Crop.objects.filter(
        status='available'
    ).values_list('district', flat=True)
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
    crop = get_object_or_404(
        Crop.objects.select_related('farmer__user', 'category'), pk=pk
    )
    related = Crop.objects.filter(
        category=crop.category, status='available'
    ).select_related('farmer__user').exclude(pk=pk)[:4]

    # check if logged in user is a farmer
    is_farmer   = False
    has_enquiry = False

    if request.user.is_authenticated:
        try:
            request.user.farmer
            is_farmer = True
        except:
            is_farmer = False

        # check if buyer already sent enquiry
        if not is_farmer:
            try:
                buyer       = request.user.buyer
                has_enquiry = Enquiry.objects.filter(
                    crop=crop, buyer=buyer
                ).exists()
            except:
                has_enquiry = False

    if request.method == 'POST' and request.user.is_authenticated:
        try:
            buyer = request.user.buyer
            form  = EnquiryForm(request.POST)
            if form.is_valid():
                enquiry       = form.save(commit=False)
                enquiry.crop  = crop
                enquiry.buyer = buyer
                enquiry.save()
                messages.success(request, "Enquiry sent! Farmer will contact you soon.")
            else:
                messages.error(request, "Please fill in all fields correctly!")
        except:
            messages.error(request, "Only buyers can send enquiries!")
        return redirect(f'/crop/{pk}/')

    return render(request, 'market/crop_detail.html', {
        'crop'       : crop,
        'related'    : related,
        'form'       : EnquiryForm(),
        'has_enquiry': has_enquiry,
        'is_farmer'  : is_farmer,
    })

# ── FARMER DASHBOARD ─────────────────────────────────
@login_required
def farmer_dashboard(request):
    try:
        farmer = request.user.farmer
    except:
        return redirect('/home/')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ADD CROP
        if action == 'add_crop':
            form = CropForm(request.POST, request.FILES)
            if form.is_valid():
                crop        = form.save(commit=False)
                crop.farmer = farmer
                crop.save()
                messages.success(request, f"'{crop.name}' added successfully!")
            else:
                for field, errors in form.errors.items():
                    messages.error(request, f"{field}: {errors[0]}")
            return redirect('/farmer-dashboard/')

        # DELETE CROP
        elif action == 'delete_crop':
            crop_id = request.POST.get('crop_id')
            try:
                crop = Crop.objects.get(id=crop_id, farmer=farmer)
                name = crop.name
                crop.delete()
                messages.success(request, f"'{name}' deleted!")
            except:
                messages.error(request, "Crop not found!")
            return redirect('/farmer-dashboard/')

        # MARK ENQUIRY READ
        elif action == 'mark_read':
            enquiry_id = request.POST.get('enquiry_id')
            try:
                enquiry         = Enquiry.objects.get(id=enquiry_id, crop__farmer=farmer)
                enquiry.is_read = True
                enquiry.save()
                messages.success(request, "Enquiry marked as read!")
            except:
                pass
            return redirect('/farmer-dashboard/')

        # REPLY TO ENQUIRY
        elif action == 'reply_enquiry':
            enquiry_id = request.POST.get('enquiry_id')
            reply_msg  = request.POST.get('reply_message', '').strip()
            if not reply_msg:
                messages.error(request, "Reply message cannot be empty!")
                return redirect('/farmer-dashboard/')
            try:
                enquiry         = Enquiry.objects.get(id=enquiry_id, crop__farmer=farmer)
                enquiry.is_read = True
                enquiry.save()
                EnquiryReply.objects.update_or_create(
                    enquiry  = enquiry,
                    defaults = {'message': reply_msg}
                )
                messages.success(request, "Reply sent to buyer!")
            except:
                messages.error(request, "Enquiry not found!")
            return redirect('/farmer-dashboard/')

    crops           = Crop.objects.filter(farmer=farmer).select_related('category')
    categories      = Category.objects.all()
    enquiries       = Enquiry.objects.filter(
        crop__farmer=farmer
    ).select_related('buyer__user', 'crop').order_by('-created')
    total_crops     = crops.count()
    available_crops = crops.filter(status='available').count()
    sold_crops      = crops.filter(status='sold').count()
    total_enquiries = enquiries.count()
    unread          = enquiries.filter(is_read=False).count()
    chats = ChatRoom.objects.filter(farmer=farmer).select_related('buyer__user', 'crop').order_by('-created')

    return render(request, 'market/farmer_dashboard.html', {
        'farmer'         : farmer,
        'crops'          : crops,
        'categories'     : categories,
        'enquiries'      : enquiries,
        'chats'          : chats,   
        'crop_form'      : CropForm(),
        'total_crops'    : total_crops,
        'available_crops': available_crops,
        'sold_crops'     : sold_crops,
        'total_enquiries': total_enquiries,
        'unread'         : unread,
    })


# ── BUYER DASHBOARD ───────────────────────────────────
@login_required
def buyer_dashboard(request):
    try:
        buyer = request.user.buyer
    except:
        return redirect('/home/')

    enquiries = Enquiry.objects.filter(
        buyer=buyer
    ).select_related('crop__farmer__user', 'crop__category').prefetch_related('reply').order_by('-created')

    # get all chat rooms for this buyer
    chat_rooms = ChatRoom.objects.filter(
        buyer=buyer
    ).select_related('farmer__user', 'crop').order_by('-created')

    return render(request, 'market/buyer_dashboard.html', {
        'buyer'          : buyer,
        'enquiries'      : enquiries,
        'total_enquiries': enquiries.count(),
        'chat_rooms'     : chat_rooms,
    })

# ── EDIT PROFILE ─────────────────────────────────────
@login_required
def edit_profile(request):
    if request.method == 'POST':
        user            = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name  = request.POST.get('last_name', '').strip()
        user.email      = request.POST.get('email', '').strip()
        user.save()

        try:
            farmer           = user.farmer
            farmer.phone     = request.POST.get('phone', '')
            farmer.district  = request.POST.get('district', '')
            farmer.state     = request.POST.get('state', '')
            farmer.farm_id   = request.POST.get('farm_id', '')
            farmer.specialty = request.POST.get('specialty', '')
            farmer.bio       = request.POST.get('bio', '')
            farmer.save()
        except:
            pass

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

    return render(request, 'market/edit_profile.html')


# ── EDIT CROP ─────────────────────────────────────────
@login_required
def edit_crop(request, pk):
    try:
        farmer = request.user.farmer
    except:
        return redirect('/home/')

    crop = get_object_or_404(Crop, pk=pk, farmer=farmer)

    if request.method == 'POST':
        form = CropForm(request.POST, request.FILES, instance=crop)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{crop.name}' updated successfully!")
            return redirect('/farmer-dashboard/')
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field}: {errors[0]}")
    else:
        form = CropForm(instance=crop)

    return render(request, 'market/edit_crop.html', {
        'crop'      : crop,
        'form'      : form,
        'categories': Category.objects.all(),
    })

@login_required
def chat_room(request, room_id):
    from .models import ChatRoom, ChatMessage
    try:
        room = ChatRoom.objects.get(pk=room_id)
    except:
        return redirect('/home/')

    user = request.user

    # allow both farmer AND buyer of this room
    is_farmer = hasattr(user, 'farmer') and user.farmer == room.farmer
    is_buyer  = hasattr(user, 'buyer')  and user.buyer  == room.buyer

    if not is_farmer and not is_buyer:
        messages.error(request, "You don't have access to this chat!")
        return redirect('/home/')

    messages_qs = ChatMessage.objects.filter(
        room=room
    ).select_related('sender').order_by('timestamp')

    return render(request, 'market/chat_room.html', {
        'room'    : room,
        'messages': messages_qs,
        'user'    : user,
    })


@login_required
def start_chat(request, crop_pk):
    from .models import ChatRoom
    crop = get_object_or_404(Crop, pk=crop_pk)

    # get buyer — if user is farmer, redirect to their chats
    try:
        buyer = request.user.buyer
    except:
        messages.error(request, "Only buyers can start a chat!")
        return redirect(f'/crop/{crop_pk}/')

    # get or create chat room between this buyer and crop's farmer
    room, created = ChatRoom.objects.get_or_create(
        farmer = crop.farmer,
        buyer  = buyer,
        crop   = crop,
    )
    return redirect(f'/chat/{room.pk}/')

@login_required
def farmer_start_chat(request, enquiry_pk):
    from .models import ChatRoom
    try:
        farmer = request.user.farmer
    except:
        return redirect('/home/')

    enquiry = get_object_or_404(Enquiry, pk=enquiry_pk, crop__farmer=farmer)

    # get or create chat room for this enquiry
    room, created = ChatRoom.objects.get_or_create(
        farmer = farmer,
        buyer  = enquiry.buyer,
        crop   = enquiry.crop,
    )
    return redirect(f'/chat/{room.pk}/')