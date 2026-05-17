from .models import Cart, Order

def user_role(request):
    is_farmer   = False
    is_buyer    = False
    cart_count  = 0
    notif_count = 0

    if request.user.is_authenticated:
        try:
            request.user.farmer
            is_farmer   = True
            # farmer notification = pending orders waiting for action
            # farmer notification
            notif_count = Order.objects.filter(
                farmer=request.user.farmer,
                status='pending',
                farmer_seen=False
            ).count()
        except:
            pass
        try:
            request.user.buyer
            is_buyer   = True
            cart_count = Cart.objects.filter(
                buyer=request.user.buyer
            ).count()
            # buyer notification = orders that changed status recently
            # (confirmed or dispatched — farmer acted on them)
            notif_count = Order.objects.filter(
                buyer=request.user.buyer,
                status__in=['confirmed', 'dispatched'],
                buyer_seen=False
            ).count()
        except:
            pass

    return {
        'is_farmer'  : is_farmer,
        'is_buyer'   : is_buyer,
        'cart_count' : cart_count,
        'notif_count': notif_count,
    }