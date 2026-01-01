from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def customer_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='users:login'):
    """
    Decorator for views that checks that the user is a customer (not staff/admin),
    redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and not u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator

def admin_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='users:login'):
    """
    Decorator for views that checks that the user is an admin,
    redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator