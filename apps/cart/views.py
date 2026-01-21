from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from products.models import Product
from .models import Cart, CartItem
from .forms import CartAddProductForm
from users.decoraters import customer_required

@customer_required
def cart_detail(request):
    """Display the cart contents"""
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all().select_related('product', 'product__category')
        
        # Check if products are still available
        for item in cart_items:
            if not item.product.available:
                messages.warning(
                    request, 
                    f"'{item.product.name}' is currently unavailable. Please remove it from your cart."
                )
            elif not item.product.in_stock:
                messages.warning(
                    request,
                    f"'{item.product.name}' is out of stock. Please update your cart."
                )
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'is_empty': not cart_items.exists(),
        }
        
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        print(f"ERROR in cart_detail: {str(e)}")
        messages.error(request, f"Unable to load your cart: {str(e)}")
        return redirect('products:product_list')

@customer_required
@require_http_methods(["POST"])
def cart_add(request, product_id):
    """Add a product to the cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        product = get_object_or_404(Product, id=product_id)
        
        if not product.available:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f"Sorry, {product.name} is currently unavailable."
                }, status=400)
            messages.error(request, f"Sorry, {product.name} is currently unavailable.")
            return redirect('products:product_list')
        
        if not product.in_stock:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f"Sorry, {product.name} is out of stock."
                }, status=400)
            messages.error(request, f"Sorry, {product.name} is out of stock.")
            return redirect('products:product_list')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        form = CartAddProductForm(request.POST or None)
        
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            override = form.cleaned_data['override']
        else:
            # Fallback to POST data
            try:
                quantity = int(request.POST.get('quantity', 1))
                override = request.POST.get('override', 'false').lower() == 'true'
            except (ValueError, TypeError):
                quantity = 1
                override = False
        
        with transaction.atomic():
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not item_created:
                new_quantity = quantity if override else cart_item.quantity + quantity
                max_warning = None
                
                if new_quantity > 20:
                    max_warning = "Maximum quantity per item is 20. Updated to maximum allowed."
                    new_quantity = 20
                
                cart_item.quantity = new_quantity
                cart_item.save()
            else:
                max_warning = None
        
        # Refresh cart to get updated counts
        cart.refresh_from_db()
        
        if is_ajax:
            response_data = {
                'success': True,
                'total_items': cart.total_items,
                'total_price': float(cart.total_price),
                'message': f"Added {product.name} to cart!"
            }
            if max_warning:
                response_data['warning'] = max_warning
            
            return JsonResponse(response_data)
        else:
            messages.success(request, f"Added {product.name} to cart!")
            if max_warning:
                messages.warning(request, max_warning)
            
            redirect_url = request.META.get('HTTP_REFERER', 'products:product_list')
            return redirect(redirect_url)
    
    except Product.DoesNotExist:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "Product not found."
            }, status=404)
        messages.error(request, "Product not found.")
        return redirect('products:product_list')
    
    except Exception as e:
        print(f"ERROR in cart_add: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)
        messages.error(request, f"An error occurred while adding to cart: {str(e)}")
        return redirect('products:product_list')

@customer_required
@require_http_methods(["POST"])
def cart_remove(request, product_id):
    """Remove a product from the cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        
        cart_item = CartItem.objects.get(cart=cart, product=product)
        product_name = cart_item.product.name
        cart_item.delete()
        
        # Refresh cart to get updated counts
        cart.refresh_from_db()
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'total_items': cart.total_items,
                'total_price': float(cart.total_price),
                'message': f"Removed {product_name} from cart!"
            })
        else:
            messages.success(request, f"Removed {product_name} from cart!")
            return redirect('cart:cart_detail')
    
    except CartItem.DoesNotExist:
        error_msg = "Item not found in your cart."
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('cart:cart_detail')
    
    except Exception as e:
        print(f"ERROR in cart_remove: {str(e)}")
        error_msg = "An error occurred while removing item."
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': error_msg
            }, status=500)
        messages.error(request, error_msg)
        return redirect('cart:cart_detail')

@customer_required
@require_http_methods(["POST"])
def cart_update(request, product_id):
    """Update product quantity in cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        print(f"DEBUG: cart_update called for product {product_id}")
        print(f"DEBUG: Request user: {request.user}")
        print(f"DEBUG: POST data: {request.POST}")
        
        # Get product
        product = get_object_or_404(Product, id=product_id)
        print(f"DEBUG: Found product: {product.name}")
        
        # Get or create cart
        try:
            cart = Cart.objects.get(user=request.user)
            print(f"DEBUG: Found cart for user")
        except Cart.DoesNotExist:
            print(f"DEBUG: Cart not found for user")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Cart not found'
                }, status=404)
            messages.error(request, 'Cart not found')
            return redirect('cart:cart_detail')
        
        # Parse quantity
        try:
            quantity = int(request.POST.get('quantity', 1))
            print(f"DEBUG: Parsed quantity: {quantity}")
        except (ValueError, TypeError) as e:
            print(f"ERROR parsing quantity: {e}")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid quantity value'
                }, status=400)
            messages.error(request, 'Invalid quantity value')
            return redirect('cart:cart_detail')
        
        # Validate quantity
        if quantity < 0:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Quantity cannot be negative'
                }, status=400)
            messages.error(request, 'Quantity cannot be negative')
            return redirect('cart:cart_detail')
        
        # Get cart item
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            print(f"DEBUG: Found cart item, current qty: {cart_item.quantity}")
        except CartItem.DoesNotExist:
            print(f"ERROR: Cart item not found")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Item not found in cart'
                }, status=404)
            messages.error(request, 'Item not found in cart')
            return redirect('cart:cart_detail')
        
        # Handle quantity update
        if quantity == 0:
            # Remove item if quantity is 0
            print(f"DEBUG: Removing item (qty=0)")
            cart_item.delete()
            cart.refresh_from_db()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                    'product_id': product_id,
                    'message': f"Removed {product.name} from cart!"
                })
            else:
                messages.success(request, f"Removed {product.name} from cart!")
                return redirect('cart:cart_detail')
        
        elif quantity > 20:
            # Enforce maximum quantity
            print(f"DEBUG: Quantity {quantity} exceeds max, setting to 20")
            quantity = 20
            cart_item.quantity = quantity
            cart_item.save()
            cart.refresh_from_db()
            cart_item.refresh_from_db()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                    'item_total_price': float(cart_item.total_price),
                    'product_id': product_id,
                    'warning': "Maximum quantity per item is 20."
                })
            else:
                messages.warning(request, "Maximum quantity per item is 20.")
                return redirect('cart:cart_detail')
        
        else:
            # Normal update
            print(f"DEBUG: Updating quantity to {quantity}")
            cart_item.quantity = quantity
            cart_item.save()
            cart.refresh_from_db()
            cart_item.refresh_from_db()
            
            print(f"DEBUG: Cart total_items: {cart.total_items}, total_price: {cart.total_price}")
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': cart.total_items,
                    'total_price': float(cart.total_price),
                    'item_total_price': float(cart_item.total_price),
                    'product_id': product_id,
                    'message': f"Updated quantity to {quantity}"
                })
            else:
                messages.success(request, f"Updated {product.name} quantity to {quantity}!")
                return redirect('cart:cart_detail')
    
    except Exception as e:
        print(f"ERROR in cart_update: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('cart:cart_detail')

@customer_required
@require_http_methods(["POST"])
def cart_clear(request):
    """Clear all items from cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items_count = cart.items.count()
        
        if cart_items_count > 0:
            cart.items.all().delete()
            cart.refresh_from_db()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': 0,
                    'total_price': 0.0,
                    'message': f"Cart cleared! Removed {cart_items_count} items."
                })
            else:
                messages.success(request, f"Cart cleared! Removed {cart_items_count} items.")
                return redirect('cart:cart_detail')
        else:
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': 0,
                    'total_price': 0.0,
                    'message': "Your cart is already empty."
                })
            messages.info(request, "Your cart is already empty.")
            return redirect('cart:cart_detail')
    
    except Exception as e:
        print(f"ERROR in cart_clear: {str(e)}")
        error_msg = "An error occurred while clearing the cart."
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': error_msg
            }, status=500)
        messages.error(request, error_msg)
        return redirect('cart:cart_detail')

@login_required
def cart_get_count(request):
    """API endpoint to get current cart count"""
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return JsonResponse({
            'success': True,
            'total_items': cart.total_items,
            'total_price': float(cart.total_price)
        })
    except Exception as e:
        print(f"ERROR in cart_get_count: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)