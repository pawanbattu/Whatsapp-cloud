import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class WhatsAppAdminUser(models.Model):
    """
    Represents a WhatsApp Business Account connection.
    Holds the API keys and is owned by your Admin users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
     
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
    )
    
    name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,  
        help_text=_("Internal name for this connection (e.g., 'Sales Team Number')")
    )

     
    access_token = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,  
        help_text=_("System User Access Token from Meta Developer Portal")
    )

    templates_access_token = models.CharField(
        max_length=500, 
        help_text=_("Template access token"),
        blank=True, 
        null=True,  
    )

    phone_number_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,  
        help_text=_("The specific Phone Number ID sending the messages")
    )
    waba_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_("WhatsApp Business Account ID (Optional, good for templates)")
    )
    app_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_("WhatsApp APP Account ID"))
    
    message_base_version = models.CharField(
        max_length=10, 
        blank=False,
        default="v17.0",
        help_text=_("WhatsApp messages base version")
    )

    templates_base_version = models.CharField(
        max_length=10, 
        blank=False,
        default="v18.0",
        help_text=_("WhatsApp templates base version")
    )

    oauth_base_version = models.CharField(
        max_length=10, 
        blank=False,
        default="v19.0",
        help_text=_("WhatsApp oauth base version")
    )


    app_secret = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_("WhatsApp Business App secret")
    )
    

    
     
    webhook_verify_token = models.CharField(
        max_length=100, 
        default=uuid.uuid4,  
        help_text=_("Token used to verify incoming webhooks from Meta")
    )

    subscribed_fields = models.CharField(max_length=255, null=True, blank=True, default=True)
    domain = models.CharField(max_length=255, null=True, blank=True, default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)  

    class Meta:
        verbose_name = _("WhatsAppAdminUser")
        verbose_name_plural = _("WhatsAppAdminUser")

    def __str__(self):
        return (
            f"{self.id} "
            f"{self.owner} "
            f"{self.name} "
            f"{self.access_token} "
            f"{self.templates_access_token} "
            f"{self.phone_number_id} "
            f"{self.waba_id} "
            f"{self.app_id} "
            f"{self.webhook_verify_token} "
            f"{self.is_active} "
            f"{self.created_at} "
            f"{self.last_edited} "
            f"{self.subscribed_fields} "
            )