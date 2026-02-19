from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from apps.core.email_utils import send_template_email
from .forms import CustomerCreationForm, CustomAuthenticationForm
from .decoraters import customer_required, staff_required, owner_required, staff_or_owner_required
from .models import CustomUser
import threading
import logging

logger = logging.getLogger(__name__)

def send_login_notification_email_async(user, request):
    """
    Send login notification email asynchronously in a separate thread
    This prevents blocking the login process
    """
    def send_email_thread():
        try:
            if not user.email or not user.email.strip():
                return
            
            # Get user's IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            context = {
                'user': user,
                'customer_name': user.get_full_name() or user.username,
                'login_time': timezone.now(),
                'ip_address': ip_address,
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'bakery_name': 'Live Bakery',
            }
            
            subject = "Welcome to Live Bakery - First Login Notification"
            
            send_template_email(
                to_email=user.email,
                subject=subject,
                template_name='emails/login_notification',
                context=context,
                fail_silently=True
            )
            logger.info(f"Login notification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending login notification email: {e}")
    
    # Start email sending in a separate thread
    email_thread = threading.Thread(target=send_email_thread)
    email_thread.daemon = True  # Thread will not prevent program from exiting
    email_thread.start()
    
    return True  # Return immediately without waiting for email to send


def send_login_notification_email(user, request):
    """
    DEPRECATED: Use send_login_notification_email_async instead
    Send login notification email to user only if they have an email address registered
    """
    if not user.email or not user.email.strip():
        # User doesn't have an email address registered, skip sending email
        return False
    
    # Get user's IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    context = {
        'user': user,
        'customer_name': user.get_full_name() or user.username,
        'login_time': timezone.now(),
        'ip_address': ip_address,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
        'bakery_name': 'Live Bakery',
    }
    
    subject = "Welcome to Live Bakery - First Login Notification"
    
    return send_template_email(
        to_email=user.email,
        subject=subject,
        template_name='emails/login_notification',
        context=context,
        fail_silently=True  # Don't break login process if email fails
    )

@csrf_protect
def custom_login(request):
    if request.user.is_authenticated:
        if request.user.user_type == 'owner' or request.user.is_superuser:
            return redirect('admin:index')
        elif request.user.user_type == 'staff':
            return redirect('admin:index')
        else:
            return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        login_type = request.POST.get('login_type', 'customer')
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Validate user type matches selected login type
                if login_type == 'customer' and user.user_type != 'customer':
                    error_message = 'Invalid credentials for customer login. Please select the correct login type.'
                elif login_type == 'staff' and user.user_type != 'staff':
                    error_message = 'Invalid credentials for staff login. Please select the correct login type.'
                elif login_type == 'admin' and user.user_type != 'owner':
                    error_message = 'Invalid credentials for admin login. Please select the correct login type.'
                else:
                    # Valid login - proceed
                    remember_me = request.POST.get('remember_me') == 'on'  # Checkbox sends 'on' when checked
                    
                    login(request, user)
                    
                    # Handle Remember Me with persistent token
                    if remember_me:
                        # Create remember me token
                        remember_token = user.create_remember_token()
                        
                        # Set the remember me cookie
                        response = None  # We'll set this in the redirect response
                        
                        # Set session to persist for 2 weeks
                        request.session.set_expiry(1209600)
                        request.session.cycle_key()  # Generate new session key for security
                        
                        # Store remember token in session for setting cookie later
                        request.session['remember_token'] = remember_token
                    else:
                        # Clear any existing remember tokens
                        user.clear_remember_tokens()
                        # Session expires when browser closes
                        request.session.set_expiry(0)
                    
                    first_name = user.first_name if user.first_name else user.username
                    
                    # Send login notification email asynchronously for first-time logins
                    is_first_login = not user.first_login_completed
                    
                    if user.email and is_first_login:
                        # Send email asynchronously (non-blocking)
                        send_login_notification_email_async(user, request)
                    
                    # Mark first login as completed
                    if is_first_login:
                        user.first_login_completed = True
                        user.save(update_fields=['first_login_completed'])
                    
                    # Redirect based on user type
                    if user.user_type == 'owner' or user.is_superuser:
                        if is_first_login:
                            message = f'Welcome to Live Bakery, {first_name}! (Owner)'
                        else:
                            message = f'Welcome back, {first_name}! (Owner)'
                        request.session['notification'] = {
                            'type': 'info',
                            'message': message
                        }
                        response = redirect('admin:index')
                    elif user.user_type == 'staff':
                        if is_first_login:
                            message = f'Welcome to Live Bakery, {first_name}! (Staff)'
                        else:
                            message = f'Welcome back, {first_name}! (Staff)'
                        request.session['notification'] = {
                            'type': 'info',
                            'message': message
                        }
                        response = redirect('admin:index')
                    else:
                        if is_first_login:
                            message = f'Welcome to Live Bakery, {first_name}! 🎉'
                        else:
                            message = f'Welcome back, {first_name}! 🎉'
                        request.session['notification'] = {
                            'type': 'success',
                            'message': message
                        }
                        request.session.save()
                        response = redirect('core:home')
                    
                    # Set remember me cookie if token was created
                    if remember_me and 'remember_token' in request.session:
                        remember_token = request.session.pop('remember_token')
                        # Set secure, HTTP-only cookie that expires in 2 weeks
                        response.set_cookie(
                            'remember_token',
                            remember_token,
                            max_age=1209600,  # 2 weeks in seconds
                            httponly=True,    # Prevent JavaScript access
                            secure=request.is_secure(),  # HTTPS only in production
                            samesite='Lax'    # CSRF protection
                        )
                    
                    return response
                
                # If we reach here, there was a user type mismatch
                return render(request, 'users/login.html', {
                    'form': form,
                    'error_notification': {
                        'type': 'error',
                        'message': error_message
                    },
                    'selected_login_type': login_type
                })
        
        # Login failed - invalid credentials
        error_message = 'Invalid username/email or password.'
        return render(request, 'users/login.html', {
            'form': form,
            'error_notification': {
                'type': 'error',
                'message': error_message
            },
            'selected_login_type': login_type
        })
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

def register(request):
    if request.user.is_authenticated:
        if request.user.user_type == 'owner':
            return redirect('admin:index')
        elif request.user.user_type == 'staff':
            return redirect('admin:index')
        else:
            return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Authenticate the user with our custom backend
            from django.contrib.auth import authenticate
            authenticated_user = authenticate(
                request=request,
                username=user.username,
                password=form.cleaned_data['password1']
            )
            
            if authenticated_user:
                login(request, authenticated_user)
                first_name = authenticated_user.first_name if authenticated_user.first_name else authenticated_user.username
                
                # Store notification data in session
                request.session['notification'] = {
                    'type': 'success',
                    'message': f'Account created successfully! Welcome to Live Bakery, {first_name}! 🍰'
                }
                request.session.save()  # Ensure session is saved
                
                return redirect('core:home')
            else:
                # Fallback: login with backend specified
                user.backend = 'apps.users.backends.EmailOrUsernameModelBackend'
                login(request, user)
                first_name = user.first_name if user.first_name else user.username
                
                # Store notification data in session
                request.session['notification'] = {
                    'type': 'success',
                    'message': f'Account created successfully! Welcome to Live Bakery, {first_name}! 🍰'
                }
                request.session.save()  # Ensure session is saved
                
                return redirect('core:home')
    else:
        form = CustomerCreationForm()
    
    return render(request, 'users/register.html', {'form': form})

def custom_logout(request):
    user_first_name = request.user.first_name or request.user.username
    
    # Clear remember me tokens for this user
    if request.user.is_authenticated:
        request.user.clear_remember_tokens()
    
    logout(request)
    
    # Store notification in session for display on redirect
    request.session['notification'] = {
        'type': 'success',
        'message': f'You have been successfully logged out. Goodbye, {user_first_name}! 👋'
    }
    request.session.save()  # Ensure session is saved
    
    # Create response and clear remember me cookie
    response = redirect('core:home')
    response.delete_cookie('remember_token')
    
    return response

@login_required
def profile(request):
    """Profile view accessible to all user types"""
    # Determine user type
    is_customer = request.user.user_type == 'customer'
    is_staff = request.user.user_type == 'staff'
    is_owner = request.user.user_type == 'owner' or request.user.is_superuser
    
    context = {
        'user': request.user,
        'is_customer': is_customer,
        'is_staff': is_staff,
        'is_owner': is_owner,
    }
    return render(request, 'users/profile.html', context)

@login_required
@customer_required
def user_orders(request):
    from orders.models import Order
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1
    }
    return render(request, 'users/orders.html', context)


# Password Reset Views

@csrf_protect
def password_reset_request(request):
    """Handle password reset request"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            return render(request, 'users/password_reset.html', {
                'error': 'Please enter your email address.'
            })
        
        # Find user by email
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists or not (security)
            return redirect('users:password_reset_done')
        
        # Generate token and uid
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset link
        reset_link = request.build_absolute_uri(
            f'/users/password-reset-confirm/{uid}/{token}/'
        )
        
        # Send email asynchronously
        def send_reset_email():
            try:
                context = {
                    'user': user,
                    'customer_name': user.get_full_name() or user.username,
                    'reset_link': reset_link,
                    'bakery_name': 'Live Bakery',
                    'valid_hours': 24,
                }
                
                send_template_email(
                    to_email=user.email,
                    subject='Password Reset Request - Live Bakery',
                    template_name='emails/password_reset',
                    context=context,
                    fail_silently=True
                )
                logger.info(f"Password reset email sent to {user.email}")
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")
        
        # Send email in background thread
        email_thread = threading.Thread(target=send_reset_email)
        email_thread.daemon = True
        email_thread.start()
        
        return redirect('users:password_reset_done')
    
    return render(request, 'users/password_reset.html')


def password_reset_done(request):
    """Show confirmation that reset email was sent"""
    return render(request, 'users/password_reset_done.html')


@csrf_protect
def password_reset_confirm(request, uidb64, token):
    """Handle password reset confirmation with new password"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    # Verify token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            # Validate passwords
            if not password1 or not password2:
                return render(request, 'users/password_reset_confirm.html', {
                    'validlink': True,
                    'error': 'Please enter both password fields.',
                    'uidb64': uidb64,
                    'token': token,
                })
            
            if password1 != password2:
                return render(request, 'users/password_reset_confirm.html', {
                    'validlink': True,
                    'error': 'Passwords do not match.',
                    'uidb64': uidb64,
                    'token': token,
                })
            
            if len(password1) < 8:
                return render(request, 'users/password_reset_confirm.html', {
                    'validlink': True,
                    'error': 'Password must be at least 8 characters long.',
                    'uidb64': uidb64,
                    'token': token,
                })
            
            # Set new password
            user.set_password(password1)
            user.save()
            
            # Log the user out of all sessions for security
            from django.contrib.sessions.models import Session
            for session in Session.objects.all():
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(user.id):
                    session.delete()
            
            logger.info(f"Password reset successful for user {user.username}")
            
            return redirect('users:password_reset_complete')
        
        # GET request - show password reset form
        return render(request, 'users/password_reset_confirm.html', {
            'validlink': True,
            'uidb64': uidb64,
            'token': token,
        })
    else:
        # Invalid token
        return render(request, 'users/password_reset_confirm.html', {
            'validlink': False,
        })


def password_reset_complete(request):
    """Show confirmation that password was reset successfully"""
    return render(request, 'users/password_reset_complete.html')