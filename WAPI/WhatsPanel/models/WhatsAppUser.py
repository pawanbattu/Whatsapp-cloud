from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from .WhatsAppAdminUser import *
import uuid


class WhatsAppUser(models.Model):
    id = models.AutoField(primary_key = True)

    phone_number = models.CharField(
        max_length=30, 
        help_text=_("The phone number with country code, typically formatted with a leading '+'.")
    )
    wa_id = models.CharField(
        max_length=50, 
        unique=True, 
        help_text=_("The WhatsApp ID returned by the API. Usually the phone number without the '+'.")
    )

    whatsapp_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text=_("The profile name the user has set on their WhatsApp account.")
    )
    
    is_opted_in = models.BooleanField(
        default=False,
        help_text=_("Has the user explicitly opted in to receive proactive template messages?")
    )
    opted_in_at = models.DateTimeField(
        null=True, 
        blank=True
    )
    is_valid_whatsapp_number = models.BooleanField(
        default=True,
        help_text=_("Set to False if the API returns an error indicating the number is not on WhatsApp.")
    )
    last_user_message_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_("The timestamp of the last message received from this user. Starts the 24h window.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.CharField(max_length=10)

    whatsapp_admin = models.ForeignKey(
        WhatsAppAdminUser, 
        on_delete=models.CASCADE, 
        db_column="owner_id",
        null=True, 
        blank=True,
    )

    class Meta:
        verbose_name = _("WhatsApp User")
        verbose_name_plural = _("WhatsApp Users")
        ordering = ['-last_user_message_at', '-created_at']

    def __str__(self):
        return (
            f"{self.id}"
            f"{self.phone_number}"
            f"{self.wa_id}"
            f"{self.whatsapp_name or 'No Name'}"
            f"{self.is_opted_in}"
            f"{self.opted_in_at}"
            f"{self.is_valid_whatsapp_number}"
            f"{self.last_user_message_at}"
            f"{self.avatar}"
            f"{self.created_at}"
            f"{self.updated_at}"
            f"{self.whatsapp_admin}"
        )

    @property
    def in_24h_window(self):
        """
        WhatsApp requires businesses to reply within 24 hours of a user's last message 
        with free-form text. Outside this window, only approved Templates can be sent.
        """
        if not self.last_user_message_at:
            return False
        return timezone.now() <= (self.last_user_message_at + timedelta(hours=24))

    def update_interaction(self):
        """Call this method whenever an incoming webhook fires for this user."""
        self.last_user_message_at = timezone.now()
        self.save(update_fields=['last_user_message_at'])