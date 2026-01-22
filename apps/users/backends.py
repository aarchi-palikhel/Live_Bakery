from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either
    their username or email address.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            # Try to find user by username or email
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None


class RememberMeBackend(ModelBackend):
    """
    Authentication backend for remember me tokens
    """
    
    def authenticate(self, request, remember_token=None, **kwargs):
        if not remember_token:
            return None
        
        try:
            from .models import RememberMeToken
            token_obj = RememberMeToken.objects.select_related('user').get(
                token=remember_token,
                expires_at__gt=timezone.now()
            )
            
            if token_obj.is_valid():
                # Mark token as used
                token_obj.use_token()
                return token_obj.user
                
        except RememberMeToken.DoesNotExist:
            pass
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None