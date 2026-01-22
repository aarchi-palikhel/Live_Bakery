from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from apps.core.email_utils import send_template_email
from .forms import CustomerCreationForm, CustomAuthenticationForm
from .decoraters import customer_required, staff_required, owner_required, staff_or_owner_required

def send_login_notification_email(user, request):
    """
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
    
    subject = "Login Notification - Live Bakery"
    
    return send_template_email(
        to_email=user.email,
        subject=subject,
        template_name='emails/login_notification',
        context=context,
        fail_silently=True  # Don't break login process if email fails
    )

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
                    
                    # Send login notification email (only if user has email and remember me is not checked)
                    email_sent = False
                    if not remember_me and user.email:
                        # Check if we already sent a login email recently to prevent duplicates
                        import time
                        
                        login_email_sent_key = f'login_email_sent_{user.id}'
                        last_sent_time = request.session.get(login_email_sent_key, 0)
                        current_time = time.time()
                        
                        # Only send email if more than 30 seconds have passed since last email
                        if current_time - last_sent_time > 30:
                            email_sent = send_login_notification_email(user, request)
                            if email_sent:
                                # Record the time we sent the email
                                request.session[login_email_sent_key] = current_time
                    
                    # Redirect based on user type
                    if user.user_type == 'owner' or user.is_superuser:
                        message = f'Welcome back, {first_name}! (Owner)'
                        if email_sent:
                            message += ' A login notification has been sent to your email.'
                        request.session['notification'] = {
                            'type': 'info',
                            'message': message
                        }
                        response = redirect('admin:index')
                    elif user.user_type == 'staff':
                        message = f'Welcome back, {first_name}! (Staff)'
                        if email_sent:
                            message += ' A login notification has been sent to your email.'
                        request.session['notification'] = {
                            'type': 'info',
                            'message': message
                        }
                        response = redirect('admin:index')
                    else:
                        message = f'Welcome back, {first_name}! 🎉'
                        if email_sent:
                            message += ' A login notification has been sent to your email.'
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
@customer_required
def profile(request):
    context = {
        'user': request.user,
        'is_customer': True
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