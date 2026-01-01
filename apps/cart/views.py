from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from products.models import Product
from .models import Cart, CartItem
from .forms import CartAddProductForm
from users.decoraters import customer_required

@customer_required
def cart_detail(request):
    """Display the cart contents"""
    try:
        print(f"DEBUG: cart_detail called for user {request.user}")
        print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        print(f"DEBUG: Cart {'created' if created else 'found'}, ID: {cart.id}")
        
        cart_items = cart.items.all().select_related('product', 'product__category')
        print(f"DEBUG: Cart items count: {cart_items.count()}")
        
        # Debug each item
        for item in cart_items:
            print(f"DEBUG: Item: {item.product.name}, Qty: {item.quantity}")
            print(f"DEBUG: Product available: {item.product.available}, in_stock: {item.product.in_stock}")
            
            # Check if product is still available and in stock
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
            'cart_item_count': cart.total_items
        }
        
        print(f"DEBUG: Rendering cart_detail.html")
        return render(request, 'cart/cart_detail.html', context)
        
    except Exception as e:
        print(f"ERROR in cart_detail: {str(e)}")
        print(f"ERROR Type: {type(e).__name__}")
        
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR Traceback:\n{error_details}")
        
        messages.error(request, f"Unable to load your cart: {str(e)}")
        return redirect('products:product_list')

@customer_required
def cart_add(request, product_id):
    """Add a product to the cart"""
    print(f"DEBUG: cart_add called for product {product_id}")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: User: {request.user}, Authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: POST data: {request.POST}")
    
    try:
        product = get_object_or_404(Product, id=product_id)
        print(f"DEBUG: Found product: {product.name}")
        print(f"DEBUG: Product available: {product.available}, in_stock: {product.in_stock}")
        
        # Check if product is available (boolean field)
        if not product.available:
            print(f"DEBUG: Product not available")
            messages.error(request, f"Sorry, {product.name} is currently unavailable.")
            return redirect('products:product_list')
        
        # Check if product is in stock (boolean field)
        if not product.in_stock:
            print(f"DEBUG: Product not in stock")
            messages.error(request, f"Sorry, {product.name} is out of stock.")
            return redirect('products:product_list')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        print(f"DEBUG: Cart {'created' if created else 'found'} for user")
        
        # Try to use the form, but fall back to simple POST data
        form = CartAddProductForm(request.POST or None)
        print(f"DEBUG: Form initialized, is_valid will be checked")
        
        if request.method == 'POST':
            print(f"DEBUG: Form is_valid: {form.is_valid()}")
            print(f"DEBUG: Form errors: {form.errors if not form.is_valid() else 'None'}")
            
            if form.is_valid():
                quantity = form.cleaned_data['quantity']
                override = form.cleaned_data['override']
                print(f"DEBUG: Form valid - quantity: {quantity}, override: {override}")
            else:
                # Fall back to simple POST data
                print(f"DEBUG: Form invalid, falling back to POST data")
                try:
                    quantity = int(request.POST.get('quantity', 1))
                    override = request.POST.get('override', 'false').lower() == 'true'
                    print(f"DEBUG: POST data - quantity: {quantity}, override: {override}")
                except (ValueError, TypeError) as e:
                    print(f"DEBUG: Error parsing POST data: {e}")
                    quantity = 1
                    override = False
            
            # Note: Your Product model doesn't have a stock quantity field!
            # It only has boolean fields: available and in_stock
            # You might want to add a stock_quantity field if you need to track actual quantities
            
            # Use transaction to ensure data integrity
            with transaction.atomic():
                cart_item, item_created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': quantity}
                )
                print(f"DEBUG: CartItem {'created' if item_created else 'found'}")
                
                if not item_created:
                    new_quantity = quantity if override else cart_item.quantity + quantity
                    print(f"DEBUG: Updating quantity from {cart_item.quantity} to {new_quantity}")
                    
                    # Check against maximum allowed quantity (20)
                    if new_quantity > 20:
                        print(f"DEBUG: New quantity {new_quantity} exceeds maximum 20")
                        messages.warning(
                            request,
                            f"Maximum quantity per item is 20. Updated to maximum allowed."
                        )
                        new_quantity = 20
                    
                    cart_item.quantity = new_quantity
                    cart_item.save()
                    print(f"DEBUG: CartItem saved with quantity {cart_item.quantity}")
            
            messages.success(request, f"Added {product.name} to cart!")
            print(f"DEBUG: Success message set")
            
            # Handle AJAX requests
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                print(f"DEBUG: AJAX request detected")
                return JsonResponse({
                    'success': True,
                    'cart_count': cart.total_items,
                    'message': f"Added {product.name} to cart!"
                })
            
            # Default redirect - back to product list or referrer
            redirect_url = request.META.get('HTTP_REFERER', 'products:product_list')
            print(f"DEBUG: Redirecting to: {redirect_url}")
            return redirect(redirect_url)
            
        else:
            # If it's not a POST request, redirect back
            print(f"DEBUG: Not a POST request")
            redirect_url = request.META.get('HTTP_REFERER', 'products:product_list')
            return redirect(redirect_url)
    
    except Product.DoesNotExist:
        print(f"DEBUG: Product.DoesNotExist error")
        messages.error(request, "Product not found.")
        return redirect('products:product_list')
    except Exception as e:
        print(f"DEBUG: General exception: {str(e)}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        messages.error(request, f"An error occurred while adding to cart: {str(e)}")
        return redirect('products:product_list')

@customer_required
def cart_remove(request, product_id):
    """Remove a product from the cart"""
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        
        cart_item = CartItem.objects.get(cart=cart, product=product)
        product_name = cart_item.product.name
        cart_item.delete()
        
        messages.success(request, f"Removed {product_name} from cart!")
        
        # Handle AJAX requests
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.total_items,
                'message': f"Removed {product_name} from cart!"
            })
    
    except CartItem.DoesNotExist:
        messages.error(request, "Item not found in your cart.")
    except Exception as e:
        messages.error(request, "An error occurred while removing item.")
    
    return redirect('cart:cart_detail')

@customer_required
def cart_update(request, product_id):
    """Update product quantity in cart"""
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        
        if request.method == 'POST':
            try:
                quantity = int(request.POST.get('quantity', 1))
                
                # Validate quantity
                if quantity < 0:
                    messages.error(request, "Quantity cannot be negative.")
                    return redirect('cart:cart_detail')
                
                cart_item = CartItem.objects.get(cart=cart, product=product)
                
                if quantity == 0:
                    # Remove item if quantity is 0
                    cart_item.delete()
                    messages.success(request, f"Removed {product.name} from cart!")
                    
                elif quantity > 20:
                    # Enforce maximum quantity
                    messages.warning(request, "Maximum quantity per item is 20.")
                    quantity = 20
                    cart_item.quantity = quantity
                    cart_item.save()
                    messages.info(request, f"Updated {product.name} quantity to maximum (20).")
                    
                # Note: Your Product model doesn't have stock quantity
                # You can't check quantity > product.in_stock because in_stock is boolean
                # If you need stock quantity, add a stock_quantity field to Product model
                    
                else:
                    # Normal update
                    cart_item.quantity = quantity
                    cart_item.save()
                    messages.success(request, f"Updated {product.name} quantity to {quantity}!")
                
                # Handle AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    cart.refresh_from_db()
                    return JsonResponse({
                        'success': True,
                        'cart_count': cart.total_items,
                        'total_price': cart.total_price,
                        'item_total': cart_item.total_price if quantity > 0 else 0
                    })
            
            except ValueError:
                messages.error(request, "Invalid quantity value.")
            except CartItem.DoesNotExist:
                messages.error(request, "Item not found in your cart.")
    
    except Exception as e:
        messages.error(request, "An error occurred while updating cart.")
    
    return redirect('cart:cart_detail')

@customer_required
def cart_clear(request):
    """Clear all items from cart"""
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items_count = cart.items.count()
        
        if cart_items_count > 0:
            cart.items.all().delete()
            messages.success(request, f"Cart cleared! Removed {cart_items_count} items.")
        else:
            messages.info(request, "Your cart is already empty.")
        
        # Handle AJAX requests
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': 0,
                'message': 'Cart cleared successfully!'
            })
    
    except Exception as e:
        messages.error(request, "An error occurred while clearing the cart.")
    
    return redirect('cart:cart_detail')