from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartItem
from products.models import Product
from .models import Order, OrderItem, CakeDesignReference
from .forms import OrderCreateForm, CakeCustomizationForm
from users.decoraters import customer_required


def calculate_delivery_fee(address):
    """Calculate delivery fee based on address"""
    if not address:
        return 100  # Default outside Bhaktapur fee
    
    address_lower = address.lower()
    
    # Check for Kamalbinayak (free delivery)
    if 'kamalbinayak' in address_lower:
        return 0
    
    # Check for Bhaktapur (Rs. 50)
    if 'bhaktapur' in address_lower:
        return 50
    
    # Outside Bhaktapur (Rs. 100)
    return 100

@customer_required
def customize_cake(request, product_id):
    """Customize a cake before adding to cart"""
    product = get_object_or_404(Product, id=product_id, is_cake=True)
    
    if not product.available:
        messages.error(request, f"Sorry, {product.name} is currently unavailable.")
        return redirect('products:product_detail', product_id=product_id)
    
    if request.method == 'POST':
        form = CakeCustomizationForm(
            request.POST, 
            request.FILES,
            product=product
        )
        
        if form.is_valid():
            try:
                # Get the session-safe data from form
                session_data = form.get_session_data()
                
                if session_data:
                    # Store in session with product_id as key
                    request.session[f'cake_customization_{product_id}'] = session_data
                    
                    # Store reference image info if uploaded
                    if form.cleaned_data.get('reference_image'):
                        request.session[f'cake_reference_{product_id}'] = {
                            'image_name': form.cleaned_data['reference_image'].name,
                            'title': form.cleaned_data.get('reference_title'),
                            'description': form.cleaned_data.get('reference_description'),
                        }
                    
                    # Add to cart with customization
                    return add_customized_cake_to_cart(request, product_id, form)
                else:
                    messages.error(request, "Failed to save customization data.")
                    
            except Exception as e:
                messages.error(request, f"Error saving customization: {str(e)}")
                # Debug: Print the error
                import traceback
                print(f"Error in customize_cake: {e}")
                print(traceback.format_exc())
        else:
            messages.error(request, "Please correct the errors below.")
            # Debug: Show form errors
            print("Form errors:", form.errors)
    else:
        form = CakeCustomizationForm(product=product)
    
    context = {
        'product': product,
        'form': form,
    }
    
    return render(request, 'orders/customize_cake.html', context)

def add_customized_cake_to_cart(request, product_id, form):
    """Helper function to add customized cake to cart"""
    try:
        product = get_object_or_404(Product, id=product_id, is_cake=True)
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get quantity from form
        quantity = form.cleaned_data.get('quantity', 1)
        
        # Check if item already exists in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()
        
        
        weight = form.cleaned_data.get('weight')
        if weight == 'custom':
            weight_display = f"Custom: {form.cleaned_data.get('custom_weight')} lb"
        else:
            weight_display = f"{weight} lb"
        
        messages.success(request, f"✅ Added customized {product.name} to cart!")
        messages.info(request, 
                     f"Customization:  {weight_display}, "
                     f"{form.cleaned_data.get('tiers')} tier(s), "
                     f"Delivery: {form.cleaned_data.get('delivery_date')}")
        
        return redirect('cart:cart_detail')
        
    except Exception as e:
        messages.error(request, f"Error adding to cart: {str(e)}")
        return redirect('orders:customize_cake', product_id=product_id)

@customer_required
def order_create(request):
    """Create order from cart items with cake customization"""
    try:
        # Get user's cart
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all().select_related('product')
        
        if not cart_items:
            messages.warning(request, "Your cart is empty. Add items before checkout.")
            return redirect('cart:cart_detail')
        
        # Check for unavailable products
        unavailable_items = []
        for item in cart_items:
            if not item.product.available:
                unavailable_items.append(item.product.name)
            elif not item.product.in_stock:
                messages.warning(request, f"'{item.product.name}' is low on stock.")
        
        if unavailable_items:
            messages.error(request, f"The following items are unavailable: {', '.join(unavailable_items)}")
            return redirect('cart:cart_detail')
        
        # Get cake items
        cake_items = [item for item in cart_items if item.product.is_cake]
        
        # Initialize forms
        order_form = OrderCreateForm(request.POST or None)
        customization_forms = {}
        
        # Check for customization data in session for cake items
        session_customizations = {}
        for cart_item in cake_items:
            customization_key = f'cake_customization_{cart_item.product.id}'
            if customization_key in request.session:
                session_customizations[cart_item.product.id] = request.session[customization_key]
        
        # Calculate initial delivery fee (default to outside Bhaktapur)
        delivery_fee = 100
        subtotal = cart.total_price
        total = subtotal + delivery_fee
        
        if request.method == 'POST':
            # Create customization forms for each cake item
            for i, cart_item in enumerate(cake_items):
                form_key = f'cake_form_{cart_item.product.id}'
                
                # Pre-fill form with session data if available
                initial_data = None
                if cart_item.product.id in session_customizations:
                    initial_data = session_customizations[cart_item.product.id]
                
                customization_forms[i] = CakeCustomizationForm(
                    request.POST, 
                    request.FILES,
                    prefix=form_key,
                    product=cart_item.product,
                    initial=initial_data
                )
            
            # Calculate delivery fee based on address if form is valid
            if order_form.is_valid():
                address = order_form.cleaned_data.get('delivery_address', '')
                delivery_fee = calculate_delivery_fee(address)
                total = subtotal + delivery_fee
        else:
            # For GET request, initialize empty forms
            for i, cart_item in enumerate(cake_items):
                form_key = f'cake_form_{cart_item.product.id}'
                
                # Pre-fill form with session data if available
                initial_data = None
                if cart_item.product.id in session_customizations:
                    initial_data = session_customizations[cart_item.product.id]
                
                customization_forms[i] = CakeCustomizationForm(
                    prefix=form_key,
                    product=cart_item.product,
                    initial=initial_data
                )
        
        if request.method == 'POST':
            # Validate all forms
            all_valid = order_form.is_valid()
            
            # Validate all cake customization forms
            for i, cart_item in enumerate(cake_items):
                form = customization_forms[i]
                if not form.is_valid():
                    all_valid = False
            
            if all_valid:
                try:
                    with transaction.atomic():
                        # Get payment method from form
                        payment_method = order_form.cleaned_data.get('payment_method', 'cod')
                        
                        # Create order FIRST
                        order = Order.objects.create(
                            user=request.user,
                            total_amount=0,  # Will be updated after calculating items
                            payment_method=payment_method,
                            payment_status=(payment_method == 'online'),  # True for online, False for COD
                            special_instructions=order_form.cleaned_data.get('special_instructions', ''),
                            delivery_address=order_form.cleaned_data.get('delivery_address', ''),
                            phone_number=order_form.cleaned_data.get('phone_number', ''),
                            status='pending'
                        )
                        
                        # Calculate subtotal with cake tier multipliers
                        order_subtotal = 0
                        
                        # Create order items from cart items
                        for i, cart_item in enumerate(cart_items):
                            if cart_item.product.is_cake:
                                # Handle cake items with customization
                                cake_form = customization_forms[i]
                                
                                # Calculate price with tier multiplier
                                base_price = cart_item.product.base_price
                                tiers = int(cake_form.cleaned_data.get('tiers', 1))
                                tier_multiplier = {
                                    1: 1.0,
                                    2: 1.5,
                                    3: 2.0
                                }.get(tiers, 1.0)
                                
                                final_price = float(base_price) * tier_multiplier
                                quantity = cake_form.cleaned_data.get('quantity', cart_item.quantity)
                                item_total = final_price * quantity
                                order_subtotal += item_total
                                
                                order_item = OrderItem.objects.create(
                                    order=order,
                                    product=cart_item.product,
                                    quantity=quantity,
                                    price=final_price,
                                    
                                    # Cake customization fields
                                    cake_weight=cake_form.cleaned_data.get('weight'),
                                    cake_custom_weight=cake_form.cleaned_data.get('custom_weight'),
                                    cake_tiers=cake_form.cleaned_data.get('tiers'),
                                    message_on_cake=cake_form.cleaned_data.get('message_on_cake'),
                                    delivery_date=cake_form.cleaned_data.get('delivery_date'),
                                    special_instructions=cake_form.cleaned_data.get('special_instructions'),
                                )
                                
                                # Save design reference if image uploaded
                                cake_form.save_design_reference(order_item)
                                
                                # Remove customization from session
                                session_key = f'cake_customization_{cart_item.product.id}'
                                if session_key in request.session:
                                    del request.session[session_key]
                                
                            else:
                                # Handle regular items
                                item_total = float(cart_item.product.base_price) * cart_item.quantity
                                order_subtotal += item_total
                                
                                order_item = OrderItem.objects.create(
                                    order=order,
                                    product=cart_item.product,
                                    quantity=cart_item.quantity,
                                    price=cart_item.product.base_price,
                                )
                        
                        # Calculate final delivery fee
                        address = order_form.cleaned_data.get('delivery_address', '')
                        delivery_fee = calculate_delivery_fee(address)
                        
                        # Update order with final total
                        order.total_amount = order_subtotal + delivery_fee
                        order.save()
                        
                        # Clear the cart after successful order
                        cart.items.all().delete()
                        
                        messages.success(
                            request, 
                            f"✅ Order placed successfully! Your order number is {order.order_number}"
                        )
                        
                        # Redirect based on payment method
                        if payment_method == 'online':
                            # Redirect to eSewa payment page
                            # TODO: Implement eSewa integration
                            return redirect('orders:order_confirmation', order_id=order.id)
                        else:
                            # COD - go directly to confirmation
                            return redirect('orders:order_confirmation', order_id=order.id)
                        
                except Exception as e:
                    messages.error(request, f"Error creating order: {str(e)}")
                    import traceback
                    print(traceback.format_exc())  # For debugging
                    return redirect('cart:cart_detail')
            else:
                # Show form errors
                for field, errors in order_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                
                for i, form in customization_forms.items():
                    if not form.is_valid():
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Cake customization error: {error}")
        
        # Recalculate totals for display (if not POST or form invalid)
        if request.method == 'POST' and order_form.is_valid():
            # Already calculated above
            pass
        else:
            # For GET or invalid POST, calculate based on current address
            if request.method == 'POST':
                address = order_form.data.get('delivery_address', '')
            else:
                address = ''
            
            delivery_fee = calculate_delivery_fee(address)
            total = subtotal + delivery_fee
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'order_form': order_form,
            'customization_forms': customization_forms,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'cake_items': cake_items,
            'has_cakes': len(cake_items) > 0,
        }
        
        return render(request, 'orders/order_create.html', context)
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())  # For debugging
        return redirect('cart:cart_detail')
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('cart:cart_detail')

@customer_required
def order_confirmation(request, order_id):
    """Display order confirmation"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Calculate delivery fee for this order
        delivery_fee = calculate_delivery_fee(order.delivery_address)
        
        # Calculate delivery estimate (2-3 days for cakes, 1-2 days for others)
        has_cakes = order.items.filter(product__is_cake=True).exists()
        if has_cakes:
            delivery_estimate = order.created_at + timedelta(days=3)
        else:
            delivery_estimate = order.created_at + timedelta(days=2)
        
        context = {
            'order': order,
            'order_items': order.items.all().select_related('product'),
            'delivery_fee': delivery_fee,
            'delivery_estimate': delivery_estimate,
        }
        
        return render(request, 'orders/order_confirmation.html', context)
        
    except Exception as e:
        messages.error(request, "Order not found.")
        return redirect('orders:order_list')

@customer_required
def order_list(request):
    """Display user's order history"""
    # Get all orders for the user
    all_orders = Order.objects.filter(user=request.user).select_related('user').order_by('-created_at')
    
    # Filter by status if provided in URL
    status = request.GET.get('status')
    if status:
        orders = all_orders.filter(status=status)
    else:
        orders = all_orders
    
    # Calculate counts for statistics
    total_orders = all_orders.count()
    completed_count = all_orders.filter(status='completed').count()
    pending_count = all_orders.filter(status='pending').count()
    confirmed_count = all_orders.filter(status='confirmed').count()
    baking_count = all_orders.filter(status='baking').count()
    ready_count = all_orders.filter(status='ready').count()
    cancelled_count = all_orders.filter(status='cancelled').count()
    
    # Active orders = pending + confirmed + baking + ready
    active_count = pending_count + confirmed_count + baking_count + ready_count
    
    # Calculate delivery fees for each order
    for order in orders:
        order.display_delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'active_count': active_count,
        'confirmed_count': confirmed_count,
        'baking_count': baking_count,
        'ready_count': ready_count,
        'cancelled_count': cancelled_count,
    }
    
    return render(request, 'orders/order_list.html', context)

@customer_required
def order_detail(request, order_id):
    """Display order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Calculate delivery fee for this order
    delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    # Get order items
    order_items = order.items.all().select_related('product')
    
    # Get cake design references for this order
    design_references = CakeDesignReference.objects.filter(
        order=order
    ).select_related('order_item', 'order_item__product')
    
    # Calculate status index for timeline
    status_order = ['pending', 'confirmed', 'baking', 'ready', 'completed', 'cancelled']
    order.status_index = status_order.index(order.status) if order.status in status_order else 0
    
    context = {
        'order': order,
        'order_items': order_items,
        'design_references': design_references,
        'delivery_fee': delivery_fee,
    }
    
    return render(request, 'orders/order_detail.html', context)

@customer_required
def order_cancel(request, order_id):
    """Cancel an order (only if status is pending)"""
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            if order.status == 'pending':
                order.status = 'cancelled'
                order.save()
                messages.success(request, f"✅ Order {order.order_number} has been cancelled.")
            else:
                messages.error(request, "❌ Only pending orders can be cancelled.")
                
        except Exception as e:
            messages.error(request, f"❌ Error cancelling order: {str(e)}")
    
    return redirect('orders:order_list')

@customer_required
def order_track(request, order_number):
    """Track order by order number"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Calculate delivery fee
    delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    context = {
        'order': order,
        'order_items': order.items.all().select_related('product'),
        'delivery_fee': delivery_fee,
    }
    
    return render(request, 'orders/order_track.html', context)

@customer_required
def order_invoice(request, order_id):
    """Generate invoice for order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Calculate delivery fee
    delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    context = {
        'order': order,
        'order_items': order.items.all().select_related('product'),
        'delivery_fee': delivery_fee,
        'invoice_date': timezone.now().date(),
    }
    
    return render(request, 'orders/order_invoice.html', context)

@customer_required 
def order_status(request, order_id):
    """Check order status"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Calculate delivery fee
    delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    context = {
        'order': order,
        'order_items': order.items.all().select_related('product'),
        'delivery_fee': delivery_fee,
    }
    
    return render(request, 'orders/order_status.html', context)