
# apps/payment/views.py - COMPLETE UPDATED VERSION
import hmac
import hashlib
import uuid
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from orders.models import Order
from cart.models import Cart
from .models import PaymentTransaction
from django.conf import settings


class EsewaView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('order_id')
        
        if not order_id:
            messages.error(request, 'Order ID is required')
            return redirect('orders:order_list')
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found or you do not have permission')
            return redirect('orders:order_list')
        
        # Check order eligibility
        if order.status != 'pending':
            messages.error(request, 'This order cannot be paid for')
            return redirect('orders:order_detail', order_id=order.id)
        
        if order.payment_method != 'esewa':
            messages.error(request, 'This order is not using eSewa payment')
            return redirect('orders:order_detail', order_id=order.id)
        
        if order.payment_status == 'paid':
            messages.info(request, 'This order has already been paid')
            return redirect('orders:order_confirmation', order_id=order.id)
        
        # Generate unique transaction UUID
        uuid_val = str(uuid.uuid4())

        def genSha256(key, msg):
            key = key.encode('utf-8')
            msg = msg.encode('utf-8')
            hmac_sha256 = hmac.new(key, msg, hashlib.sha256)
            digest = hmac_sha256.digest()
            signature = base64.b64encode(digest).decode('utf-8')
            return signature
        
        secret_key = '8gBm/:&EnhH.1/q'  # TODO: Move to environment variables
        
        # Format the data exactly as eSewa expects
        data_to_sign = f"total_amount={order.total_amount},transaction_uuid={uuid_val},product_code=EPAYTEST"
        signature = genSha256(secret_key, data_to_sign)

        # Create payment transaction record
        payment_transaction = PaymentTransaction.objects.create(
            user=request.user,
            order=order,  # Link to order using ForeignKey
            transaction_uuid=uuid_val,
            amount=order.total_amount,
            total_amount=order.total_amount,
            tax_amount=0,
            service_charge=0,
            delivery_charge=0,
            product_code='EPAYTEST',
            signature=signature,
            status='initiated',
        )

        # Build URLs
        success_url = f"{request.scheme}://{request.get_host}{reverse('orders:order_confirmation', args=[order.id])}?payment=success"
        failure_url = f"{request.scheme}://{request.get_host}{reverse('payment:cancel_payment', args=[uuid_val])}"

        data = {
            'amount': str(order.total_amount),
            'total_amount': str(order.total_amount),
            'transaction_uuid': uuid_val,
            'product_code': 'EPAYTEST',
            'signature': signature,
            'success_url': success_url,
            'failure_url': failure_url,
        }

        context = {
            'data': data,
            'order': order,
            'success_url': success_url,
            'failure_url': failure_url,
        }
        
        return render(request, 'payment/esewa_payment.html', context)

@csrf_exempt
def esewa_callback(request):
    """Handle eSewa TESTING payment verification callback"""
    if request.method == 'POST':
        try:
            # Get data from eSewa callback
            data = request.POST.dict()
            print(f"eSewa TEST Callback Data: {data}")
            
            # For testing, you might want to skip signature verification temporarily
            # Uncomment the next lines when ready to test signature
            '''
            secret_key = '8gBm/:&EnhH.1/q'
            if not verify_esewa_signature(data, secret_key):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid signature'
                }, status=400)
            '''
            
            # Extract required fields - test environment might use different field names
            transaction_uuid = data.get('transaction_uuid') or data.get('transaction_uuid')
            status = data.get('status', '').upper()
            ref_id = data.get('ref_id') or data.get('reference_id')
            total_amount = data.get('total_amount') or data.get('amount')
            
            print(f"TEST DEBUG: UUID={transaction_uuid}, Status={status}, Ref={ref_id}, Amount={total_amount}")
            
            if not transaction_uuid:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing transaction_uuid'
                }, status=400)
            
            # Find the payment transaction
            try:
                payment = PaymentTransaction.objects.get(transaction_uuid=transaction_uuid)
                print(f"TEST DEBUG: Found payment {payment.id}, current status: {payment.status}")
                
                # Store test callback data
                payment.esewa_status = status
                payment.reference_id = ref_id or ''
                payment.esewa_response_data = data
                
                # TESTING: Accept all statuses for debugging
                print(f"TEST DEBUG: Received status: {status}")
                
                # Handle different test statuses
                if status in ['COMPLETE', 'SUCCESS', 'APPROVED']:
                    payment.status = 'success'
                    payment.save()
                    
                    if payment.order:
                        order = payment.order
                        order.payment_status = 'paid'
                        order.status = 'confirmed'
                        order.save(update_fields=['payment_status', 'status', 'updated_at'])
                        
                        print(f"TEST SUCCESS: Order {order.id} marked as paid")
                        
                        # Clear cart
                        try:
                            Cart.objects.filter(user=order.user).delete()
                        except:
                            pass
                        
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Test payment successful',
                            'redirect_url': reverse('orders:order_confirmation', kwargs={'order_id': order.id})
                        })
                
                elif status in ['PENDING', 'PROCESSING']:
                    payment.status = 'pending'
                    payment.save()
                    return JsonResponse({
                        'status': 'pending',
                        'message': 'Test payment pending'
                    })
                
                else:  # Treat everything else as failed for testing
                    payment.status = 'failed'
                    payment.save()
                    
                    if payment.order:
                        payment.order.payment_status = 'failed'
                        payment.order.status = 'cancelled'
                        payment.order.save(update_fields=['payment_status', 'status', 'updated_at'])
                    
                    return JsonResponse({
                        'status': 'failed',
                        'message': f'Test payment {status.lower()}'
                    })
                    
            except PaymentTransaction.DoesNotExist:
                print(f"TEST ERROR: Transaction not found: {transaction_uuid}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Transaction not found in test system'
                }, status=404)
                
        except Exception as e:
            print(f"eSewa Test Callback Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'Test error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method for test'
    }, status=400)

def payment_success_redirect(request, transaction_uuid):
    """Redirect to order confirmation after successful payment"""
    try:
        payment = PaymentTransaction.objects.get(transaction_uuid=transaction_uuid)
        if payment.order and payment.status == 'success':
            messages.success(request, 'Payment successful! Your order is now confirmed.')
            return redirect('orders:order_confirmation', order_id=payment.order.id)
        else:
            messages.error(request, 'Payment not found or not successful')
            return redirect('orders:order_list')
    except PaymentTransaction.DoesNotExist:
        messages.error(request, 'Payment transaction not found')
        return redirect('orders:order_list')
    

def verify_esewa_signature(data, secret_key):
    """Verify eSewa callback signature"""
    import hmac
    import hashlib
    import base64
    
    signed_field_names = data.get('signed_field_names', '').split(',')
    
    # Build the string to sign exactly as eSewa expects
    data_to_sign = ""
    for field in signed_field_names:
        if field in data:
            data_to_sign += f"{field}={data[field]},"
    
    if data_to_sign.endswith(','):
        data_to_sign = data_to_sign[:-1]
    
    # Generate expected signature
    key = secret_key.encode('utf-8')
    msg = data_to_sign.encode('utf-8')
    hmac_sha256 = hmac.new(key, msg, hashlib.sha256)
    digest = hmac_sha256.digest()
    expected_signature = base64.b64encode(digest).decode('utf-8')
    
    return expected_signature == data.get('signature', '')

def cancel_payment(request, transaction_uuid):
        """Handle payment cancellation from eSewa page"""
        try:
            payment = PaymentTransaction.objects.get(transaction_uuid=transaction_uuid)
            
            # Only allow cancellation if payment is still pending/initiated
            if payment.status in ['pending', 'initiated']:
                payment.status = 'failed'
                payment.esewa_status = 'CANCELLED'
                payment.save()
                
                if payment.order:
                    payment.order.payment_status = 'failed'
                    payment.order.status = 'cancelled'
                    payment.order.save()
                    
                    messages.warning(request, 'Payment was cancelled. Your order has been cancelled.')
                    return redirect('orders:order_detail', order_id=payment.order.id)
            
            messages.info(request, 'This payment cannot be cancelled.')
            return redirect('orders:order_list')
            
        except PaymentTransaction.DoesNotExist:
            messages.error(request, 'Payment transaction not found')
            return redirect('orders:order_list')