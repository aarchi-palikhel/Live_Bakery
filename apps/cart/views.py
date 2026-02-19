import traceback
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from products.models import Product
from .models import Cart, CartItem
from users.decoraters import customer_required

# Set up logging
logger = logging.getLogger('cart')

def get_cart_totals(cart):
    """Helper function to safely get cart totals"""
    total_items = 0
    total_price = 0
    
    for item in cart.items.all():
        total_items += item.quantity
        # Handle price field name variations
        product_price = getattr(item.product, 'base_price', None) or getattr(item.product, 'price', 0)
        total_price += float(product_price) * item.quantity
    
    return total_items, total_price

@login_required
def cart_detail(request):
    """Display the cart contents"""
    # Check if user is staff or admin
    if request.user.user_type in ['staff', 'owner'] or request.user.is_superuser:
        return render(request, 'cart/cart_staff_message.html', {
            'user_type': request.user.user_type
        })
    
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all().select_related('product', 'product__category')
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'is_empty': not cart_items.exists(),
        }
        
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in cart_detail for user {request.user.id}: {str(e)}", exc_info=True)
        messages.error(request, "Unable to load your cart")
        return redirect('products:product_list')

@csrf_protect
@customer_required
@require_http_methods(["POST"])
def cart_add(request, product_id):
    """Add a product to the cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        # Get product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': "Product not found."
                }, status=404)
            messages.error(request, "Product not found.")
            return redirect('products:product_list')
        
        # Get quantity
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1
        
        # Check availability
        if hasattr(product, 'available') and not product.available:
            msg = f"Sorry, {product.name} is currently unavailable."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('products:product_list')
        
        # Check stock
        if hasattr(product, 'in_stock') and not product.in_stock:
            msg = f"Sorry, {product.name} is out of stock."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('products:product_list')
        
        # Check stock quantity
        if hasattr(product, 'stock_quantity') and product.stock_quantity > 0:
            if not product.has_stock(quantity):
                msg = f"Sorry, only {product.stock_quantity} units of {product.name} available."
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('products:product_list')
        
        max_warning = None
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Remove transaction.atomic() - SQLite doesn't handle it well
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > 20:
                max_warning = "Maximum quantity per item is 20. Updated to maximum allowed."
                new_quantity = 20
            cart_item.quantity = new_quantity
            cart_item.save()
        
        cart.refresh_from_db()
        total_items, total_price = get_cart_totals(cart)
        
        if is_ajax:
            response_data = {
                'success': True,
                'total_items': total_items,
                'total_price': total_price,
                'message': f"Added {product.name} to cart!"
            }
            if max_warning:
                response_data['warning'] = max_warning
            return JsonResponse(response_data)
        else:
            messages.success(request, f"Added {product.name} to cart!")
            if max_warning:
                messages.warning(request, max_warning)
            return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))
    
    except Exception as e:
        logger.error(f"Error in cart_add for user {request.user.id}, product {product_id}: {str(e)}", exc_info=True)
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "An error occurred while adding to cart"
            }, status=500)
        messages.error(request, "An error occurred while adding to cart")
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
        cart.refresh_from_db()
        
        total_items, total_price = get_cart_totals(cart)
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'total_price': total_price,
                'message': f"Removed {product_name} from cart!"
            })
        messages.success(request, f"Removed {product_name} from cart!")
        return redirect('cart:cart_detail')
    
    except CartItem.DoesNotExist:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "Item not found in cart"
            }, status=404)
        messages.error(request, "Item not found in cart")
        return redirect('cart:cart_detail')
    
    except Exception as e:
        logger.error(f"Error in cart_remove for user {request.user.id}, product {product_id}: {str(e)}", exc_info=True)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "An error occurred"
            }, status=500)
        messages.error(request, "An error occurred")
        return redirect('cart:cart_detail')

@customer_required
@require_http_methods(["POST"])
def cart_update(request, product_id):
    """Update product quantity in cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            CartItem.objects.filter(cart=cart, product=product).delete()
            cart.refresh_from_db()
            total_items, total_price = get_cart_totals(cart)
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'total_items': total_items,
                    'total_price': total_price,
                    'message': f"Removed {product.name} from cart!"
                })
            messages.success(request, f"Removed {product.name} from cart!")
            return redirect('cart:cart_detail')
        
        if quantity > 20:
            quantity = 20
        
        # Check stock availability
        if hasattr(product, 'stock_quantity') and product.stock_quantity > 0:
            if not product.has_stock(quantity):
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f"Sorry, only {product.stock_quantity} units available."
                    }, status=400)
                messages.error(request, f"Sorry, only {product.stock_quantity} units available.")
                return redirect('cart:cart_detail')
        
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.quantity = quantity
        cart_item.save()
        cart.refresh_from_db()
        
        total_items, total_price = get_cart_totals(cart)
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'total_price': total_price,
                'message': 'Cart updated!'
            })
        messages.success(request, 'Cart updated!')
        return redirect('cart:cart_detail')
    
    except Exception as e:
        logger.error(f"Error in cart_update for user {request.user.id}, product {product_id}: {str(e)}", exc_info=True)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "An error occurred"
            }, status=500)
        messages.error(request, "An error occurred")
        return redirect('cart:cart_detail')

@customer_required
@require_http_methods(["POST"])
def cart_clear(request):
    """Clear all items from cart"""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    try:
        cart = get_object_or_404(Cart, user=request.user)
        CartItem.objects.filter(cart=cart).delete()
        cart.refresh_from_db()
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'total_items': 0,
                'total_price': 0,
                'message': 'Cart cleared!'
            })
        messages.success(request, 'Cart cleared!')
        return redirect('cart:cart_detail')
    
    except Exception as e:
        logger.error(f"Error in cart_clear for user {request.user.id}: {str(e)}", exc_info=True)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': "An error occurred"
            }, status=500)
        return redirect('cart:cart_detail')

@login_required
@require_http_methods(["GET"])
def cart_get_count(request):
    """API endpoint to get current cart count"""
    try:
        cart = Cart.objects.get(user=request.user)
        total_items, total_price = get_cart_totals(cart)
        return JsonResponse({
            'success': True,
            'total_items': total_items,
            'total_price': total_price
        })
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': True,
            'total_items': 0,
            'total_price': 0
        })
    except Exception as e:
        logger.error(f"Error in cart_get_count for user {request.user.id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': "Error getting cart count"
        }, status=500)