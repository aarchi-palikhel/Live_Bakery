from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartItem
from products.models import Product
from .models import Order, OrderItem, CakeDesignReference
from .forms import OrderCreateForm, CakeCustomizationForm
from users.decoraters import customer_required
from django_esewa import EsewaPayment
import uuid
from django.conf import settings
from payment.models import PaymentTransaction
from django.views.decorators.csrf import csrf_exempt
import traceback
import io
import os
from utils.invoice_generator import InvoiceGenerator

@customer_required
def create_order_with_payment(request):
    """Create order with eSewa payment integration - AJAX endpoint"""
    if request.method == 'POST':
        try:
            # Get user's cart
            cart = get_object_or_404(Cart, user=request.user)
            cart_items = cart.items.all().select_related('product')
            
            if not cart_items:
                return JsonResponse({
                    'success': False,
                    'message': 'Your cart is empty.'
                })
            
            # Parse form data
            delivery_type = request.POST.get('delivery_type', 'delivery')
            delivery_address = request.POST.get('delivery_address', '')
            phone_number = request.POST.get('phone_number', '')
            special_instructions = request.POST.get('special_instructions', '')
            payment_method = request.POST.get('payment_method', 'cod')
            
            # Calculate delivery fee (0 for pickup)
            if delivery_type == 'pickup':
                delivery_fee = 0
            else:
                delivery_fee = calculate_delivery_fee(delivery_address)
            
            # Calculate subtotal
            subtotal = cart.total_price
            total_amount = subtotal + delivery_fee
            
            with transaction.atomic():
                # Create order with ALL required fields
                order = Order.objects.create(
                    user=request.user,
                    delivery_type=delivery_type,
                    delivery_address=delivery_address if delivery_type == 'delivery' else '',
                    phone_number=phone_number,
                    special_instructions=special_instructions,
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    total_amount=total_amount,
                    payment_method=payment_method,
                    payment_status='pending',
                    status='pending'
                )
                
                # Create order items from cart
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.base_price,
                    )
                
                # Handle payment based on method
                if payment_method == 'esewa':
                    # Create payment transaction - FIXED: Remove order_id parameter
                    payment = PaymentTransaction.objects.create(
                        user=request.user,
                        order=order,  # Just pass the order object
                        amount=order.total_amount,
                        total_amount=order.total_amount,
                        tax_amount=0,
                        service_charge=0,
                        delivery_charge=delivery_fee,
                        status='initiated',
                        product_code='EPAYTEST',
                    )
                    
                    # IMPORTANT: Clear cart after creating order
                    cart.items.all().delete()
                    
                    # Return payment URL for eSewa
                    return JsonResponse({
                        'success': True,
                        'order_id': order.id,
                        'payment_url': f'/payment/esewa/?order_id={order.id}',
                        'message': 'Order created. Proceed to payment.'
                    })
                
                else:
                    # For COD, mark as pending
                    order.payment_status = 'pending'
                    order.status = 'confirmed'
                    order.save()
                    
                    # Clear cart
                    cart.items.all().delete()
                    
                    return JsonResponse({
                        'success': True,
                        'order_id': order.id,
                        'payment_url': None,
                        'redirect_url': f'/orders/confirmation/{order.id}/',
                        'message': 'Order created successfully.'
                    })
                    
        except Exception as e:
            print(f"Error creating order with payment: {str(e)}")
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error creating order: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


def calculate_delivery_fee(address):
    """Calculate delivery fee based on address"""
    if not address:
        return 100  # Default outside Bhaktapur fee
    
    address_lower = address.lower()
    
    # Check for Kamalbinayak (Rs. 20)
    if 'kamalbinayak' in address_lower:
        return 20
    
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
                print(f"Error in customize_cake: {e}")
                traceback.print_exc()
        else:
            messages.error(request, "Please correct the errors below.")
            print("Form errors:", form.errors)
    else:
        form = CakeCustomizationForm(product=product)
    
    context = {
        'product': product,
        'form': form,
    }
    
    return render(request, 'orders/customize_cake.html', context)


@customer_required
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
    print(f"=== DEBUG ORDER_CREATE ===")
    print(f"DEBUG: Method: {request.method}")
    print(f"DEBUG: User: {request.user}")
    
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
        
        # Calculate initial totals
        subtotal = cart.total_price
        delivery_fee = 100  # Default outside Bhaktapur fee
        total = subtotal + delivery_fee
        
        if request.method == 'POST':
            # Check if this is an AJAX request for eSewa payment
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return create_order_with_payment(request)
            
            # Regular form submission
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
            
            # Validate order form first
            if order_form.is_valid():
                # Calculate delivery fee based on address
                address = order_form.cleaned_data.get('delivery_address', '')
                delivery_fee = calculate_delivery_fee(address)
                total = subtotal + delivery_fee
                
                # Validate all cake customization forms
                all_valid = True
                for i, cart_item in enumerate(cake_items):
                    form = customization_forms[i]
                    if not form.is_valid():
                        all_valid = False
                        # Show form errors
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Cake customization error ({cart_item.product.name}): {error}")
                
                if all_valid:
                    try:
                        with transaction.atomic():
                            # Get form data
                            delivery_type = order_form.cleaned_data.get('delivery_type', 'delivery')
                            payment_method = order_form.cleaned_data.get('payment_method', 'cod')
                            phone_number = order_form.cleaned_data.get('phone_number', '')
                            special_instructions = order_form.cleaned_data.get('special_instructions', '')
                            
                            print(f"DEBUG: Creating order for user {request.user.id}")
                            
                            # Create the order with calculated totals
                            order = Order.objects.create(
                                # User information
                                user=request.user,
                                
                                # Delivery information
                                delivery_type=delivery_type,
                                delivery_address=address if delivery_type == 'delivery' else '',
                                delivery_fee=delivery_fee,
                                
                                # Contact information
                                phone_number=phone_number,
                                special_instructions=special_instructions,
                                
                                # Payment information
                                payment_method=payment_method,
                                payment_status='pending',
                                
                                # Status
                                status='pending',
                                
                                # Financial information
                                subtotal=subtotal,
                                total_amount=total,
                            )
                            
                            print(f"DEBUG: Order created with ID {order.id}, Number {order.order_number}")
                            
                            # Create order items
                            for i, cart_item in enumerate(cart_items):
                                if cart_item.product.is_cake:
                                    # Handle cake items with customization
                                    cake_form = customization_forms[i]
                                    
                                    # Get customization data
                                    flavor = cake_form.cleaned_data.get('flavor', 'vanilla')
                                    custom_flavor = cake_form.cleaned_data.get('custom_flavor', '')
                                    weight = cake_form.cleaned_data.get('weight', '1')
                                    custom_weight = cake_form.cleaned_data.get('custom_weight', '')
                                    tiers = int(cake_form.cleaned_data.get('tiers', 1))
                                    message_on_cake = cake_form.cleaned_data.get('message_on_cake', '')
                                    delivery_date = cake_form.cleaned_data.get('delivery_date')
                                    cake_special_instructions = cake_form.cleaned_data.get('special_instructions', '')
                                    quantity = cake_form.cleaned_data.get('quantity', cart_item.quantity)
                                    
                                    # Calculate price with tier multiplier
                                    base_price = cart_item.product.base_price
                                    tier_multiplier = {
                                        1: 1.0,
                                        2: 1.5,
                                        3: 2.0
                                    }.get(tiers, 1.0)
                                    
                                    final_price = float(base_price) * tier_multiplier
                                    
                                    print(f"DEBUG: Creating cake order item for product {cart_item.product.id}")
                                    
                                    # Create order item with customization
                                    order_item = OrderItem.objects.create(
                                        order=order,
                                        product=cart_item.product,
                                        quantity=quantity,
                                        price=final_price,
                                        
                                        # Cake customization fields
                                        cake_flavor=flavor,
                                        cake_custom_flavor=custom_flavor,
                                        cake_weight=weight,
                                        cake_custom_weight=custom_weight,
                                        cake_tiers=tiers,
                                        message_on_cake=message_on_cake,
                                        delivery_date=delivery_date,
                                        special_instructions=cake_special_instructions,
                                    )
                                    
                                    print(f"DEBUG: Order item created with ID {order_item.id}")
                                    
                                    # Save design reference if image uploaded
                                    if hasattr(cake_form, 'save_design_reference'):
                                        try:
                                            cake_form.save_design_reference(order_item)
                                        except Exception as e:
                                            print(f"Error saving design reference: {e}")
                                            # Don't fail the whole order if design reference fails
                                    
                                    # Remove customization from session
                                    session_key = f'cake_customization_{cart_item.product.id}'
                                    if session_key in request.session:
                                        del request.session[session_key]
                                    
                                else:
                                    # Handle regular items
                                    final_price = float(cart_item.product.base_price)
                                    
                                    print(f"DEBUG: Creating regular order item for product {cart_item.product.id}")
                                    
                                    order_item = OrderItem.objects.create(
                                        order=order,
                                        product=cart_item.product,
                                        quantity=cart_item.quantity,
                                        price=final_price,
                                    )
                            
                            # Clear the cart after successful order
                            cart.items.all().delete()
                            
                            messages.success(
                                request, 
                                f"✅ Order placed successfully! Your order number is {order.order_number}"
                            )
                            
                            # Redirect based on payment method
                            if payment_method == 'esewa':
                                # Create payment transaction for eSewa - FIXED
                                try:
                                    payment = PaymentTransaction.objects.create(
                                        user=request.user,
                                        order=order,  # Just pass the order object
                                        amount=order.total_amount,
                                        total_amount=order.total_amount,
                                        tax_amount=0,
                                        service_charge=0,
                                        delivery_charge=delivery_fee,
                                        status='initiated',
                                        product_code='EPAYTEST',
                                    )
                                    
                                    print(f"DEBUG: Payment transaction created for order {order.id}")
                                    
                                    # Redirect to eSewa payment
                                    return redirect('payment:esewa_payment', order_id=order.id)
                                    
                                except Exception as e:
                                    print(f"Error creating payment transaction: {e}")
                                    messages.warning(request, "Order created but payment setup failed. Please contact support.")
                                    return redirect('orders:order_confirmation', order_id=order.id)
                                
                            else:
                                # COD - go directly to confirmation
                                print(f"DEBUG: COD order, redirecting to confirmation")
                                return redirect('orders:order_confirmation', order_id=order.id)
                            
                    except Exception as e:
                        print(f"Error creating order: {str(e)}")
                        traceback.print_exc()
                        messages.error(request, f"❌ Error creating order: {str(e)}")
                        return redirect('cart:cart_detail')
                else:
                    # Form validation failed
                    messages.error(request, "Please correct the errors below.")
            else:
                # Order form validation failed
                for field, errors in order_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        
        # For GET request or invalid POST, initialize forms
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
        
        # Recalculate totals for display
        if request.method == 'POST':
            address = request.POST.get('delivery_address', '')
        else:
            address = ''
        
        delivery_fee = calculate_delivery_fee(address)
        total = subtotal + delivery_fee
        
        # Prepare context and render template
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
        print(f"Error in order_create: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"❌ An error occurred: {str(e)}")
        return redirect('cart:cart_detail')

@customer_required
def order_confirmation(request, order_id):
    """Show order confirmation for both COD and eSewa payments"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        print(f"\n=== order_confirmation DEBUG ===")
        print(f"Order ID: {order.id}, Payment method: {order.payment_method}")
        print(f"GET params: {dict(request.GET)}")
        
        # Handle eSewa payment success
        if order.payment_method == 'esewa' and 'data' in request.GET:
            print("Processing eSewa encoded data...")
            
            try:
                import base64
                import json
                
                # Decode the base64 data
                encoded_data = request.GET.get('data')
                print(f"Encoded data: {encoded_data[:50]}...")
                
                decoded_bytes = base64.b64decode(encoded_data)
                esewa_data = json.loads(decoded_bytes.decode('utf-8'))
                
                print(f"Decoded eSewa data:")
                print(json.dumps(esewa_data, indent=2))
                
                # Extract data
                transaction_uuid = esewa_data.get('transaction_uuid')
                status = esewa_data.get('status')
                total_amount = esewa_data.get('total_amount')
                transaction_code = esewa_data.get('transaction_code')
                
                print(f"\nTransaction UUID: {transaction_uuid}")
                print(f"Status: {status}")
                print(f"Amount: {total_amount}")
                print(f"Transaction Code: {transaction_code}")
                
                # Verify signature (important!)
                # You should implement proper signature verification
                
                # Find the payment transaction
                payment = PaymentTransaction.objects.filter(
                    transaction_uuid=transaction_uuid
                ).first()
                
                if payment:
                    print(f"Found payment: {payment.id}")
                    
                    if status == 'COMPLETE':
                        # Verify amount matches
                        if float(total_amount) == float(payment.total_amount):
                            print(f"Amount verification OK: {total_amount}")
                            
                            # Update payment
                            payment.status = 'success'
                            payment.esewa_status = status
                            payment.reference_id = transaction_code
                            payment.esewa_response_data = esewa_data
                            payment.save()
                            
                            # Update order
                            order.payment_status = 'paid'
                            order.status = 'confirmed'
                            order.save()
                            
                            messages.success(request, 'Payment successful! Your order is confirmed.')
                            print(f"Updated order {order.id} to paid status")
                        else:
                            print(f"Amount mismatch! eSewa: {total_amount}, Order: {payment.total_amount}")
                            messages.error(request, 'Payment amount mismatch. Please contact support.')
                    else:
                        print(f"Payment status is {status}, not COMPLETE")
                        messages.warning(request, f'Payment status: {status}')
                else:
                    print(f"No payment found with UUID: {transaction_uuid}")
                    messages.error(request, 'Payment transaction not found.')
                    
            except Exception as e:
                print(f"Error processing eSewa data: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, 'Error processing payment data.')
        
        # Also handle the old ?payment=success parameter
        elif request.GET.get('payment') == 'success' and order.payment_method == 'esewa':
            print("Received ?payment=success parameter")
            # Check if we already have a successful payment
            successful_payment = order.payment_transactions.filter(
                status='success'
            ).first()
            
            if successful_payment:
                print(f"Found successful payment: {successful_payment.id}")
                if order.payment_status != 'paid':
                    order.payment_status = 'paid'
                    order.status = 'confirmed'
                    order.save()
                    messages.success(request, 'Payment successful!')
            else:
                print("No successful payment found yet")
                messages.info(request, 'Payment received. Processing...')
        
        # Rest of your view remains the same...
        
        context = {
            'order': order,
            'order_items': order.items.all().select_related('product'),
            'subtotal': order.subtotal or 0,
            'delivery_fee': order.delivery_fee or 0,
        }
        
        return render(request, 'orders/order_confirmation.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
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
    
    # VERIFY PAYMENT STATUS WITH ACTUAL PAYMENT TRANSACTIONS
    # Get all payment transactions for this order
    payment_transactions = order.payment_transactions.all().order_by('-created_at')
    
    # If order shows as paid but latest payment transaction shows failed, fix it
    if order.payment_status == 'paid' or order.payment_status == True:
        if payment_transactions.exists():
            latest_payment = payment_transactions.first()
            if latest_payment.status == 'failed':
                # Update order payment status to reflect reality
                order.payment_status = 'failed'
                # Also update order status if it's still pending
                if order.status == 'pending':
                    order.status = 'cancelled'
                order.save()
    
    # If order is pending but has failed payments, update status
    elif order.status == 'pending' and payment_transactions.exists():
        latest_payment = payment_transactions.first()
        if latest_payment.status == 'failed':
            order.payment_status = 'failed'
            order.save()
    
    # Calculate delivery fee for this order
    delivery_fee = calculate_delivery_fee(order.delivery_address)
    
    # Get order items
    order_items = order.items.all().select_related('product')
    
    # CALCULATE SUBTOTAL
    subtotal = 0
    for item in order_items:
        # Calculate item total
        item_total = item.price * item.quantity
        # You can also set this as a property on each item for use in template
        item.item_total = item_total
        subtotal += item_total
    
    # Get cake design references for this order
    design_references = CakeDesignReference.objects.filter(
        order=order
    ).select_related('order_item', 'order_item__product')
    
    # Calculate status index for timeline
    status_order = ['pending', 'confirmed', 'baking', 'ready', 'completed', 'cancelled']
    order.status_index = status_order.index(order.status) if order.status in status_order else 0
    
    # Get payment method display text
    payment_method_display = dict(Order.PAYMENT_CHOICES).get(order.payment_method, order.payment_method)
    
    context = {
        'order': order,
        'order_items': order_items,
        'design_references': design_references,
        'delivery_fee': delivery_fee,
        'subtotal': subtotal,  # Added subtotal here
        'payment_transactions': payment_transactions,
        'payment_method_display': payment_method_display,
        'latest_payment': payment_transactions.first() if payment_transactions.exists() else None,
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

@login_required
def order_invoice_pdf(request, order_id):
    """Download order invoice as PDF"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Generate PDF
    generator = InvoiceGenerator(order)
    pdf = generator.generate()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'invoice_{order.order_number}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

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


@csrf_exempt
def handle_payment_callback(request):
    """Handle eSewa payment callback"""
    if request.method == 'POST':
        try:
            data = request.POST.dict()
            transaction_uuid = data.get('transaction_uuid')
            reference_id = data.get('reference_id')
            status = data.get('status')
            
            if not transaction_uuid:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid transaction'
                })
            
            # Find the payment transaction
            try:
                payment = PaymentTransaction.objects.get(transaction_uuid=transaction_uuid)
                
                # Update payment status
                if status == 'COMPLETE':
                    payment.status = 'success'
                    payment.reference_id = reference_id
                    payment.esewa_status = status
                    
                    # Update order status
                    order = payment.order
                    if order:
                        order.payment_status = 'paid'
                        order.status = 'confirmed'  # Move to confirmed after payment
                        order.save()
                        
                        # Send confirmation email or notification
                        messages.success(
                            request, 
                            f"Payment successful! Order #{order.id} is now confirmed."
                        )
                else:
                    payment.status = 'failed'
                    payment.esewa_status = status
                    
                    # Update order status
                    order = payment.order
                    if order:
                        order.payment_status = 'failed'
                        order.save()
                
                payment.esewa_response_data = data
                payment.save()
                
                return JsonResponse({
                    'success': True,
                    'order_id': order.id if order else None,
                    'status': payment.status
                })
                
            except PaymentTransaction.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Payment transaction not found'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error processing payment: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@customer_required
def payment_status(request, order_id):
    """Display payment status after eSewa callback"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Get payment success message from session if available
        payment_success = request.session.pop('payment_success', None)
        payment_error = request.session.pop('payment_error', None)
        
        context = {
            'order': order,
            'payment_success': payment_success,
            'payment_error': payment_error,
        }
        
        return render(request, 'orders/payment_status.html', context)
        
    except Exception as e:
        messages.error(request, "Order not found.")
        return redirect('orders:order_list')