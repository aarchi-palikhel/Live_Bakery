# views.py
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from .models import Product, Category, ProductImage
from .forms import ProductSearchForm
from django.contrib.auth.decorators import login_required
from cart.forms import CartAddProductForm
from orders.forms import CakeCustomizationForm

def product_list(request, category_slug=None):
    """Display list of products with optional category filtering"""
    category = None
    categories = Category.objects.all()
    
    # Get all available products from database with optimized queries
    products = Product.objects.filter(available=True).select_related('category').prefetch_related('images').order_by('-is_featured', 'name')
    
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
        'cart_forms': paginated_cart_forms,
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, product_id):
    """Display detailed view of a single product"""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        id=product_id,
        available=True
    )
    
    # Get related products (same category, excluding current) with optimized query
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]
    
    # Prepare cake customization form data if product is a cake
    cake_form = None
    if product.is_cake:
        cake_form = CakeCustomizationForm(product=product)
    
    # Handle AJAX add to cart
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = CartAddProductForm(request.POST)
        if form.is_valid():
            # Get or create cart
            cart = request.session.get('cart', {})
            product_id_str = str(product.id)
            
            quantity = form.cleaned_data['quantity']
            override = form.cleaned_data.get('override', False)
            
            if product_id_str in cart and not override:
                cart[product_id_str]['quantity'] += quantity
            else:
                cart[product_id_str] = {
                    'quantity': quantity,
                    'price': str(product.base_price)
                }
            
            request.session['cart'] = cart
            request.session.modified = True
            
            # Calculate total items in cart
            total_items = sum(item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'message': f'{product.name} added to cart!',
                'cart_item_count': total_items,
                'product_name': product.name
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid form data'
            })
    
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
    products = Product.objects.filter(available=True).select_related('category').prefetch_related('images')
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

# Helper function to get cart count (used in template context processor if needed)
def get_cart_count(request):
    cart = request.session.get('cart', {})
    return sum(item['quantity'] for item in cart.values())