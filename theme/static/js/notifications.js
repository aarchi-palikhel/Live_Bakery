/**
 * Global notifications system
 * Use this consistently across all pages
 */

class NotificationManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupContainer();
                this.displayStoredNotifications();
            });
        } else {
            this.setupContainer();
            this.displayStoredNotifications();
        }
    }

    setupContainer() {
        // Get existing container or create new one
        this.container = document.getElementById('notifications-container');
        
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notifications-container';
            this.container.style.position = 'fixed';
            this.container.style.top = '90px';
            this.container.style.right = '16px';
            this.container.style.zIndex = '50';
            this.container.style.display = 'flex';
            this.container.style.flexDirection = 'column';
            this.container.style.gap = '8px';
            this.container.style.maxWidth = '384px';
            this.container.style.pointerEvents = 'none';
            
            document.body.appendChild(this.container);
        }
        
        this.adjustPosition();
        window.addEventListener('resize', () => this.adjustPosition());
    }

    adjustPosition() {
        if (!this.container) return;
        
        const width = window.innerWidth;
        
        if (width <= 640) {
            this.container.style.top = '75px';
            this.container.style.left = '8px';
            this.container.style.right = '8px';
            this.container.style.maxWidth = 'calc(100% - 16px)';
        } else if (width <= 1024) {
            this.container.style.top = '85px';
            this.container.style.left = 'auto';
            this.container.style.right = '16px';
            this.container.style.maxWidth = '384px';
        } else {
            this.container.style.top = '90px';
            this.container.style.left = 'auto';
            this.container.style.right = '16px';
            this.container.style.maxWidth = '384px';
        }
    }

    show(message, type = 'info', duration = 3000) {
        if (!this.container) {
            this.setupContainer();
        }

        const notification = document.createElement('div');
        
        // Set classes based on type
        let bgColor, textColor, icon;
        switch(type) {
            case 'success':
                bgColor = 'bg-green-500';
                textColor = 'text-white';
                icon = '✓';
                break;
            case 'error':
                bgColor = 'bg-red-500';
                textColor = 'text-white';
                icon = '✗';
                break;
            case 'warning':
                bgColor = 'bg-yellow-500';
                textColor = 'text-white';
                icon = '⚠';
                break;
            case 'info':
            default:
                bgColor = 'bg-blue-500';
                textColor = 'text-white';
                icon = 'ℹ';
        }
        
        notification.className = `${bgColor} ${textColor} p-4 rounded-lg shadow-lg transform transition-all duration-300 pointer-events-auto`;
        notification.style.animation = 'slide-in 0.3s ease-out';
        notification.innerHTML = `
            <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-3 flex-1">
                    <span class="text-xl shrink-0" style="line-height: 1;">${icon}</span>
                    <span class="text-sm sm:text-base wrap-break-word">${message}</span>
                </div>
                <button class="shrink-0 focus:outline-none hover:opacity-75 transition" 
                        onclick="this.closest('[class*=bg-]').remove()" 
                        style="padding: 0; background: none; border: none; cursor: pointer; line-height: 1;">
                    <span style="font-size: 20px;">×</span>
                </button>
            </div>
        `;
        
        // Add to container
        this.container.appendChild(notification);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.animation = 'slide-out 0.3s ease-in forwards';
                    setTimeout(() => {
                        if (notification.parentElement) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
        
        return notification;
    }

    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 4000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 3500) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }

    displayStoredNotifications() {
        let hasSessionNotification = false;
        
        // Check for session notification
        const sessionNotif = document.getElementById('session-notification');
        if (sessionNotif) {
            const type = sessionNotif.getAttribute('data-type');
            const message = sessionNotif.getAttribute('data-message');
            
            if (message && message.trim()) {
                console.log('Displaying session notification:', type, message);
                this.show(message, type, 5000);
                hasSessionNotification = true;
            }
        }

        // Check for hidden message elements (from Django forms)
        const messages = document.querySelectorAll('[data-message-type][data-message-text]');
        
        if (messages.length > 0) {
            messages.forEach(msgElement => {
                const type = msgElement.getAttribute('data-message-type');
                const text = msgElement.getAttribute('data-message-text');
                
                if (text && text.trim()) {
                    console.log('Displaying form message:', type, text);
                    this.show(text, type, 5000);
                }
            });
        }
        
        // Only clear session notification if there was actually one to display
        if (hasSessionNotification) {
            console.log('Clearing session notification via API call');
            this.clearSessionNotification();
        } else {
            console.log('No session notification to clear, skipping API call');
        }
    }

    clearSessionNotification() {
        // Clear session notification asynchronously
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.content;
        
        if (csrfToken) {
            fetch('/clear-notification/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            }).then(response => {
                if (response.ok) {
                    console.log('Session notification cleared successfully');
                } else {
                    console.warn('Failed to clear session notification:', response.status);
                }
            }).catch(err => {
                console.warn('Error clearing session notification:', err);
            });
        } else {
            console.warn('No CSRF token found, cannot clear session notification');
        }
    }
}

// Create global instance
const notificationManager = new NotificationManager();

// Global shorthand functions
window.showNotification = (message, type = 'info', duration = 3000) => {
    return notificationManager.show(message, type, duration);
};

window.showSuccess = (message, duration = 3000) => {
    return notificationManager.success(message, duration);
};

window.showError = (message, duration = 4000) => {
    return notificationManager.error(message, duration);
};

window.showWarning = (message, duration = 3500) => {
    return notificationManager.warning(message, duration);
};

window.showInfo = (message, duration = 3000) => {
    return notificationManager.info(message, duration);
};