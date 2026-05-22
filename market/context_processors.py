from .models import Cart, Order
from .models import Rating

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
            buyer = request.user.buyer

            # crop IDs that this buyer has already rated
            already_rated = Rating.objects.filter(
                buyer=buyer
            ).values_list('crop_id', flat=True)

            # delivered orders where crop is NOT yet rated
            notif_count = Order.objects.filter(
                buyer=buyer,
                status='delivered'
            ).exclude(
                crop_id__in=already_rated
            ).count()
        except:
            pass

    return {
        'is_farmer'  : is_farmer,
        'is_buyer'   : is_buyer,
        'cart_count' : cart_count,
        'notif_count': notif_count,
    }