# views.py
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from .models import Product, Category, ProductImage
from .forms import ProductSearchForm
from django.contrib.auth.decorators import login_required
from cart.forms import CartAddProductForm
from orders.forms import CakeCustomizationForm

def product_list(request, category_slug=None):
    """Display list of products with optional category filtering"""
    category = None
    categories = Category.objects.all()
    
    # Get all available products from database
    products = Product.objects.filter(available=True).order_by('-is_featured', 'name')
    
    # Apply category filter if provided
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Handle search if form is submitted
    form = ProductSearchForm(request.GET or None)
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category_filter = form.cleaned_data.get('category')
        
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(short_description__icontains=query) |
                Q(description__icontains=query)
            )
        
        if category_filter:
            products = products.filter(category=category_filter)
    
    # Create a dictionary of cart forms for each product
    cart_forms = {}
    for product in products:
        cart_forms[product.id] = CartAddProductForm()
    
    # Pagination - show 12 products per page
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Update forms for paginated products
    paginated_cart_forms = {}
    for product in products_page:
        paginated_cart_forms[product.id] = CartAddProductForm()
    
    context = {
        'category': category,
        'categories': categories,
        'products': products_page,  # This is the paginated queryset
        'page_obj': products_page,
        'is_paginated': products_page.has_other_pages(),
        'form': form,
        'cart_forms': paginated_cart_forms,  # Changed from add_to_cart_form
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, product_id):
    """Display detailed view of a single product"""
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'design_references'),
        id=product_id,
        available=True
    )
    
    # Get related products (same category, excluding current)
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]
    
    # Prepare cake customization form data if product is a cake
    cake_form = None
    if product.is_cake:
        
        cake_form = CakeCustomizationForm(product=product)
    
    context = {
        'product': product,
        'related_products': related_products,
        'cake_form': cake_form,
        'add_to_cart_form': CartAddProductForm(),
    }
    return render(request, 'products/product_detail.html', context)

def product_search(request):
    """Handle product search"""
    form = ProductSearchForm(request.GET or None)
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(short_description__icontains=query) |
                Q(description__icontains=query)
            )
        
        if category:
            products = products.filter(category=category)
    
    context = {
        'form': form,
        'products': products,
        'categories': categories,
        'query': request.GET.get('query', ''),
    }
    return render(request, 'products/product_search.html', context)

