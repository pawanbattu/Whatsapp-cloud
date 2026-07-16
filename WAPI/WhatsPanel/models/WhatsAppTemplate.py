from django.db import models
from django.utils.translation import gettext_lazy as _
from .WhatsAppAdminUser import *

class WhatsAppTemplate(models.Model):
    class Category(models.TextChoices):
        AUTHENTICATION = 'AUTHENTICATION', _('Authentication')
        MARKETING = 'MARKETING', _('Marketing')
        UTILITY = 'UTILITY', _('Utility')

    class Status(models.TextChoices):
        APPROVED = 'APPROVED', _('Approved')
        PENDING = 'PENDING', _('Pending')
        REJECTED = 'REJECTED', _('Rejected')
        PAUSED = 'PAUSED', _('Paused')
        DISABLED = 'DISABLED', _('Disabled')
        PENDING_DELETION = 'PENDING_DELETION', _('Pending Deletion')

     
    template_id = models.CharField(
        max_length=255, 
        unique=True, 
        blank=True, 
        null=True,
        help_text=_("The unique ID assigned by WhatsApp Cloud API upon creation.")
    )
    name = models.CharField(
        max_length=512, 
        help_text=_("The template name (e.g., 'order_confirmation'). Must be lowercase and underscores only.")
    )
    language = models.CharField(
        max_length=10, 
        default='en_US',
        help_text=_("The language code (e.g., 'en_US', 'es_ES').")
    )
    
     
    category = models.CharField(
        max_length=20, 
        choices=Category.choices, 
        default=Category.UTILITY
    )
    status = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=Status.choices, 
        default=Status.PENDING
    )
    
     
    components = models.JSONField(
        default=list,
        help_text=_("JSON array containing the template components as defined by the WhatsApp API.")
    )
    
     
    rejected_reason = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )

    parameter_format = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    ) 

    whatsapp_admin = models.ForeignKey(
        WhatsAppAdminUser, 
        on_delete=models.CASCADE, 
        db_column="user_id", 
        related_name="templates"
    )

     
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("WhatsApp Template")
        verbose_name_plural = _("WhatsApp Templates")
         
        unique_together = ('name', 'language')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.id} {self.name} {self.template_id} {self.language} {self.status} {self.category} {self.components} {self.rejected_reason} {self.created_at} {self.updated_at} {self.parameter_format}"

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED