from .models import Cart

def user_role(request):
    is_farmer  = False
    is_buyer   = False
    cart_count = 0

    if request.user.is_authenticated:
        try:
            request.user.farmer
            is_farmer = True
        except:
            pass
        try:
            request.user.buyer
            is_buyer   = True
            cart_count = Cart.objects.filter(buyer=request.user.buyer).count()
        except:
            pass

    return {
        'is_farmer' : is_farmer,
        'is_buyer'  : is_buyer,
        'cart_count': cart_count,
    }