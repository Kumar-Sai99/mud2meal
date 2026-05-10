def user_role(request):
    is_farmer = False
    is_buyer  = False

    if request.user.is_authenticated:
        try:
            request.user.farmer
            is_farmer = True
        except:
            pass
        try:
            request.user.buyer
            is_buyer = True
        except:
            pass

    return {
        'is_farmer': is_farmer,
        'is_buyer' : is_buyer,
    }