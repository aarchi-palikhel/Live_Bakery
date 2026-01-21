console.log('Cart JS loaded');

// Listen for cart updates from product_detail.js
document.addEventListener('cartUpdated', function(event) {
    console.log('Cart update event received:', event.detail);
    
    if (event.detail && event.detail.total_items !== undefined) {
        updateCartTotals(event.detail);
    }
});

// Update cart quantity with smoother animation
async function updateQuantity(form, change) {
    // Check if already updating
    if (window.cartIsUpdating) return;
    window.cartIsUpdating = true;
    
    const quantityDisplay = form.querySelector('.quantity-display');
    const minusBtn = form.querySelector('.quantity-minus');
    const plusBtn = form.querySelector('.quantity-plus');
    
    if (!quantityDisplay) {
        console.error('Quantity display not found');
        window.cartIsUpdating = false;
        return;
    }
    
    const currentQty = parseInt(quantityDisplay.textContent.trim());
    
    if (isNaN(currentQty)) {
        console.error('Could not parse quantity:', quantityDisplay.textContent);
        window.cartIsUpdating = false;
        return;
    }
    
    const newQty = currentQty + change;
    
    // Validate quantity range
    if (newQty < 1 || newQty > 20) {
        window.cartIsUpdating = false;
        return;
    }
    
    // Add click animation
    if (change > 0 && plusBtn) {
        plusBtn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            plusBtn.style.transform = '';
        }, 100);
    } else if (change < 0 && minusBtn) {
        minusBtn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            minusBtn.style.transform = '';
        }, 100);
    }
    
    // Smooth transition for quantity display
    quantityDisplay.style.transition = 'all 0.2s ease';
    quantityDisplay.style.opacity = '0.5';
    
    setTimeout(() => {
        quantityDisplay.textContent = newQty;
        quantityDisplay.style.opacity = '1';
    }, 100);
    
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    
    if (!csrfToken) {
        console.error('CSRF token not found');
        window.cartIsUpdating = false;
        showError('Security error: CSRF token missing');
        // Revert quantity on error
        quantityDisplay.textContent = currentQty;
        return;
    }
    
    const formData = new FormData(form);
    formData.set('quantity', newQty);
    
    try {
        console.log('Sending update request to:', form.action);
        console.log('New quantity:', newQty);
        
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        
        if (!response.ok) {
            console.error('Response not OK, status:', response.status);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            console.log('Update successful');
            showSuccess(data.message || `Quantity updated to ${newQty}`);
            updateCartTotals(data);
            updateButtonStates(form, newQty);
        } else {
            console.error('Update failed:', data.message);
            showError(data.message || 'Failed to update quantity');
            // Revert quantity on error
            quantityDisplay.textContent = currentQty;
            updateButtonStates(form, currentQty);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        showError('An error occurred: ' + error.message);
        quantityDisplay.textContent = currentQty;
        updateButtonStates(form, currentQty);
    } finally {
        window.cartIsUpdating = false;
    }
}

// Update button disabled states
function updateButtonStates(form, quantity) {
    const minusBtn = form.querySelector('.quantity-minus');
    const plusBtn = form.querySelector('.quantity-plus');
    
    if (minusBtn) {
        minusBtn.disabled = quantity <= 1;
        minusBtn.style.opacity = quantity <= 1 ? '0.5' : '1';
        minusBtn.style.cursor = quantity <= 1 ? 'not-allowed' : 'pointer';
    }
    
    if (plusBtn) {
        plusBtn.disabled = quantity >= 20;
        plusBtn.style.opacity = quantity >= 20 ? '0.5' : '1';
        plusBtn.style.cursor = quantity >= 20 ? 'not-allowed' : 'pointer';
    }
}

// Update cart totals dynamically
function updateCartTotals(data) {
    console.log('Updating cart totals:', data);
    
    // Update total items count - IN CART PAGE
    if (data.total_items !== undefined) {
        console.log('Updating total items to:', data.total_items);
        
        const itemsElements = document.querySelectorAll('[data-total-items]');
        console.log('Found', itemsElements.length, 'elements with data-total-items');
        itemsElements.forEach(el => {
            el.textContent = data.total_items;
        });
        
        // Update navbar cart badge
        const cartCount = document.getElementById('cart-count');
        if (cartCount) {
            console.log('Updating cart-count element');
            cartCount.textContent = data.total_items;
        }
        
        const mobileCartCount = document.getElementById('mobile-cart-count');
        if (mobileCartCount) {
            console.log('Updating mobile-cart-count element');
            mobileCartCount.textContent = data.total_items;
        }
        
        // Update cart count in header/nav - multiple selectors
        const navCartCounts = document.querySelectorAll('.cart-count, [data-cart-count]');
        console.log('Found', navCartCounts.length, 'nav cart count elements');
        navCartCounts.forEach(el => {
            el.textContent = data.total_items;
        });
    }
    
    // Update total price
    if (data.total_price !== undefined) {
        console.log('Updating total price to:', data.total_price);
        
        const priceElements = document.querySelectorAll('[data-total-price]');
        console.log('Found', priceElements.length, 'elements with data-total-price');
        
        priceElements.forEach(el => {
            el.style.transition = 'all 0.3s ease';
            el.style.opacity = '0.7';
            setTimeout(() => {
                el.textContent = `Rs. ${data.total_price}`;
                el.style.opacity = '1';
            }, 150);
        });
    }
    
    // Update individual item price if provided
    if (data.item_total_price !== undefined && data.product_id !== undefined) {
        console.log('Updating item price for product:', data.product_id);
        
        const itemElement = document.querySelector(`[data-product-id="${data.product_id}"]`);
        if (itemElement) {
            const priceEl = itemElement.querySelector('.item-total-price');
            if (priceEl) {
                priceEl.style.transition = 'all 0.3s ease';
                priceEl.style.opacity = '0.7';
                setTimeout(() => {
                    priceEl.textContent = `Rs. ${data.item_total_price}`;
                    priceEl.style.opacity = '1';
                }, 150);
            }
        }
    }
}

// Remove item with smooth animation
async function removeItem(form) {
    const cartItem = form.closest('.cart-item');
    const button = form.querySelector('[type="submit"]');
    const originalHTML = button.innerHTML;
    button.innerHTML = '<span class="animate-spin">⟳</span>';
    button.disabled = true;
    
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: new FormData(form)
        });
        
        const data = await response.json();
        console.log('Remove item response:', data);
        
        if (data.success) {
            // Smooth fade out animation
            cartItem.style.opacity = '0';
            cartItem.style.transform = 'translateX(-20px)';
            cartItem.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                cartItem.remove();
                
                // Update cart totals immediately - this updates navbar
                updateCartTotals(data);
                
                // Check if this was the last item
                if (data.total_items === 0) {
                    // Fade out the cart and show empty state
                    console.log('Cart is now empty, showing empty state');
                    setTimeout(() => {
                        fadeOutCartShowEmpty();
                    }, 300);
                } else {
                    // Show success message
                    showSuccess(data.message || 'Item removed from cart');
                }
            }, 300);
        } else {
            showError(data.message || 'Failed to remove item');
            button.disabled = false;
            button.innerHTML = originalHTML;
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred: ' + error.message);
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}

// Clear cart with smooth animation
async function clearCart(form) {
    const button = form.querySelector('[type="submit"]');
    const originalText = button.textContent;
    button.textContent = 'Clearing...';
    button.disabled = true;
    
    // Show confirmation
    if (!confirm('Are you sure you want to clear your entire cart?')) {
        button.textContent = originalText;
        button.disabled = false;
        return;
    }
    
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: new FormData(form)
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Fade out all cart items
            const cartItems = document.querySelectorAll('.cart-item');
            cartItems.forEach((item, index) => {
                setTimeout(() => {
                    item.style.opacity = '0';
                    item.style.transform = 'translateX(-20px)';
                    item.style.transition = 'all 0.3s ease';
                }, index * 100);
            });
            
            // Show empty state after animation
            setTimeout(() => {
                updateCartTotals(data);
                fadeOutCartShowEmpty();
            }, cartItems.length * 100 + 300);
        } else {
            showError(data.message || 'Failed to clear cart');
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred: ' + error.message);
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Fade out cart and show empty state
function fadeOutCartShowEmpty() {
    const gridContainer = document.querySelector('.grid.lg\\:grid-cols-3');
    
    if (gridContainer) {
        // Fade out the grid
        gridContainer.style.opacity = '0';
        gridContainer.style.transition = 'opacity 0.4s ease';
        
        setTimeout(() => {
            // Replace with empty state HTML
            const emptyStateHTML = `
                <div class="text-center py-12">
                    <div class="w-24 h-24 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                        <span class="text-3xl">🛒</span>
                    </div>
                    <h3 class="text-xl font-semibold text-gray-700 mb-2">Your cart is empty</h3>
                    <p class="text-gray-600 mb-6">Add some delicious bakery items to get started!</p>
                    <a href="/products/" class="bg-[#8f3232] text-white px-6 py-3 rounded-lg font-medium hover:bg-[#7a2a2a] inline-block transition">
                        Start Shopping
                    </a>
                </div>
            `;
            
            gridContainer.innerHTML = emptyStateHTML;
            gridContainer.style.opacity = '1';
            gridContainer.style.transition = 'opacity 0.4s ease';
            
            showSuccess('Cart cleared');
        }, 400);
    } else {
        // Fallback: reload the page
        location.reload();
    }
}

// Setup event listeners
function setupCart() {
    console.log('Setting up cart event listeners');
    
    // Quantity buttons - direct event listeners
    document.querySelectorAll('.quantity-minus').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const form = this.closest('.update-cart-form');
            if (form) {
                console.log('Minus button clicked, form:', form);
                updateQuantity(form, -1);
            }
        });
    });
    
    document.querySelectorAll('.quantity-plus').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const form = this.closest('.update-cart-form');
            if (form) {
                console.log('Plus button clicked, form:', form);
                updateQuantity(form, 1);
            }
        });
    });
    
    // Remove buttons
    document.querySelectorAll('.remove-cart-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            removeItem(this);
        });
    });
    
    // Clear cart
    const clearCartForm = document.getElementById('clear-cart-form');
    if (clearCartForm) {
        clearCartForm.addEventListener('submit', function(e) {
            e.preventDefault();
            clearCart(this);
        });
    }
    
    // Initialize button states for all items
    document.querySelectorAll('.update-cart-form').forEach(form => {
        const quantityDisplay = form.querySelector('.quantity-display');
        if (quantityDisplay) {
            const quantity = parseInt(quantityDisplay.textContent.trim());
            if (!isNaN(quantity)) {
                updateButtonStates(form, quantity);
            }
        }
    });
    
    console.log('Cart setup complete');
}

// Initialize
if (!window.cartInitialized) {
    window.cartInitialized = true;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupCart);
    } else {
        setupCart();
    }
} else {
    console.log('Cart already initialized');
}