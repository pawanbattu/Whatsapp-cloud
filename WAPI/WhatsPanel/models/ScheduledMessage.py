from django.db import models
from .WhatsAppAdminUser import *


class ScheduledMessage(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.AutoField(primary_key=True)

     
    wamid = models.CharField(max_length=255, null=True, blank=True)
    message_id = models.CharField(max_length=255, null=True, blank=True)

     
    userid = models.IntegerField()
    sender_userid = models.IntegerField(null=True, blank=True)
    

     
    wa_timestamp = models.BigIntegerField()

     
    created_at = models.DateTimeField(auto_now_add=True)

     
    message_type = models.CharField(max_length=50)

     
    text_content = models.TextField(null=True, blank=True)

     
    template = models.TextField(null=True, blank=True)
    Error = models.TextField(null=True, blank=True)

    language_code = models.CharField(max_length=10, default='en_US')
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    file = models.JSONField(null=True, blank=True)

    whatsapp_admin = models.ForeignKey(
        WhatsAppAdminUser, 
        on_delete=models.CASCADE, 
        db_column="owner_id",
        null=True,  
        blank=True, 
    )

    class Meta:
        db_table = "ScheduledMessage"

    
    def __str__(self):
        return (
            f"{self.id} "
            f"{self.wamid} "
            f"{self.message_id} "
            
            f"{self.userid} "
            f"{self.sender_userid} "
            f"{self.wa_timestamp} "
            f"{self.created_at} "
            f"{self.message_type} "
            f"{self.text_content} "
            f"{self.template} "
            f"{self.Error} "
            f"{self.language_code} "
            f"{self.scheduled_at} "
            f"{self.status} "
            f"{self.updated_at} "
            f"{self.whatsapp_admin} "
            )