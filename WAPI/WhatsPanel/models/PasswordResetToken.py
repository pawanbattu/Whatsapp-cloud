from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
class PasswordResetToken(models.Model):
    """Tracks password reset requests for built-in User accounts."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_tokens'

    def __str__(self):
        return f"PasswordResetToken({self.user.email}, used={self.is_used})"

    def is_valid(self):
        from django.conf import settings
        from datetime import timedelta
        expiry_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 24)
        expiry = self.created_at + timedelta(hours=expiry_hours)
        return not self.is_used and timezone.now() < expiry
