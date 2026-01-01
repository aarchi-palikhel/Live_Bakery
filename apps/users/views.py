from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import CustomerCreationForm, CustomAuthenticationForm

def register(request):
    # If user is already logged in, redirect them appropriately
    if request.user.is_authenticated:
        if hasattr(request.user, 'is_admin_user') and request.user.is_admin_user():
            messages.info(request, "You are already logged in as admin.")
            return redirect('admin:index')
        else:
            messages.info(request, "You are already logged in.")
            return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully! Welcome to Live Bakery!")
            return redirect('core:home')
    else:
        form = CustomerCreationForm()
    return render(request, 'users/register.html', {'form': form})

def custom_login(request):
    # If user is already logged in, redirect them appropriately
    if request.user.is_authenticated:
        if hasattr(request.user, 'is_admin_user') and request.user.is_admin_user():
            messages.info(request, "You are already logged in as admin.")
            return redirect('admin:index')
        else:
            messages.info(request, "You are already logged in.")
            return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Check if user is staff (admin) or customer
                if user.is_staff or (hasattr(user, 'is_admin_user') and user.is_admin_user()):
                    messages.info(request, f"Welcome back, Admin {user.username}!")
                    return redirect('admin:index')  # Redirect admin to admin panel
                else:
                    messages.success(request, f"Welcome back, {user.username}!")
                    return redirect('core:home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def custom_logout(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('core:home')

@login_required
def profile(request):
    # If admin tries to access customer profile, redirect them to admin
    if request.user.is_staff or (hasattr(request.user, 'is_admin_user') and request.user.is_admin_user()):
        messages.warning(request, "Admins should use the admin panel.")
        return redirect('admin:index')
    
    context = {
        'user': request.user,
        'is_customer': True
    }
    return render(request, 'users/profile.html', context)

@login_required
def user_orders(request):
    # Only customers should access this page
    if request.user.is_staff or (hasattr(request.user, 'is_admin_user') and request.user.is_admin_user()):
        messages.warning(request, "This page is for customers only. Please use the admin panel.")
        return redirect('admin:index')
    
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