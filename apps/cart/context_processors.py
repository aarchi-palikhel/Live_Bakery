from .models import Cart

def cart_context(request):
    context = {}
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_item_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_item_count'] = 0
    else:
        context['cart_item_count'] = 0
    return context