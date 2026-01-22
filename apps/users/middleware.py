from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class RememberMeMiddleware(MiddlewareMixin):
    """
    Middleware to automatically authenticate users with valid remember me tokens
    """
    
    def process_request(self, request):
        # Skip if user is already authenticated
        if request.user.is_authenticated:
            return None
        
        # Check for remember me token in cookies
        remember_token = request.COOKIES.get('remember_token')
        if not remember_token:
            return None
        
        try:
            from .models import RememberMeToken
            from django.utils import timezone
            
            # Find valid token
            token_obj = RememberMeToken.objects.select_related('user').get(
                token=remember_token,
                expires_at__gt=timezone.now()
            )
            
            if token_obj.is_valid():
                # Authenticate user
                user = token_obj.user
                
                # Use the remember me backend to authenticate
                from .backends import RememberMeBackend
                backend = RememberMeBackend()
                authenticated_user = backend.authenticate(
                    request, 
                    remember_token=remember_token
                )
                
                if authenticated_user:
                    # Log the user in
                    login(request, authenticated_user, backend='apps.users.backends.RememberMeBackend')
                    
                    # Extend session for remember me users
                    request.session.set_expiry(1209600)  # 2 weeks
                    
        except Exception as e:
            # If anything goes wrong, just continue without authentication
            # This prevents the remember me feature from breaking the site
            pass
        
        return None