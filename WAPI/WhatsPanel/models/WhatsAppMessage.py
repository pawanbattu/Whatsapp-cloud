from django.db import models
from .WhatsAppAdminUser import *


class WhatsAppMessage(models.Model):
    id = models.AutoField(primary_key=True)

     
    wamid = models.CharField(max_length=255, unique=True)

     
    userid = models.IntegerField()
    sender_userid = models.IntegerField(null=True, blank=True)
    sender_phonenumber = models.CharField(max_length=255, null=True, blank=True)

     
    wa_timestamp = models.BigIntegerField()

     
    created_at = models.DateTimeField(auto_now_add=True)

     
    message_type = models.CharField(max_length=50)

     
    text_content = models.TextField(null=True, blank=True)

     
    reply_to_wamid = models.CharField(max_length=255, null=True, blank=True)

     
    media_id = models.IntegerField(null=True, blank=True)

     
    address = models.CharField(max_length=255, null=True, blank=True)
    coordinates = models.CharField(max_length=255, null=True, blank=True)

     
    template = models.TextField(null=True, blank=True)

     
    forwarded = models.BooleanField(null=True, blank=True)
    originalSenderId = models.IntegerField(null=True, blank=True)
    originalTimestamp = models.DateTimeField(null=True, blank=True)

     
    raw_webhook_payload = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(null=True, blank=True, default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    error_text = models.TextField(null=True, blank=True)

    whatsapp_admin = models.ForeignKey(
        WhatsAppAdminUser, 
        on_delete=models.CASCADE, 
        db_column="owner_id",
        null=True, 
        blank=True, 
    )

    class Meta:
        db_table = "whatsapp_messages"

    
    def __str__(self):
        return (
            f"{self.id} "
            f"{self.wamid} "
            f"{self.userid} "
            f"{self.sender_userid} "
            f"{self.message_type} "
            f"{self.text_content} "
            f"{self.reply_to_wamid} "
            f"{self.media_id} "
            f"{self.address} "
            f"{self.coordinates} "
            f"{self.template} "
            f"{self.forwarded} "
            f"{self.originalSenderId} "
            f"{self.originalTimestamp} "
            )