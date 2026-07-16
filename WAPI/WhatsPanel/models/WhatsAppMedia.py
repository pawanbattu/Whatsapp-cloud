from django.db import models

class WhatsAppMedia(models.Model):
     
     
    id = models.BigAutoField(primary_key=True)
    
    name = models.CharField(max_length=255, help_text="Media name")
    
     
    size = models.FloatField(help_text="Media size") 
    
    type = models.CharField(max_length=100, help_text="Media type and format (e.g., image/jpeg)")
    duration = models.FloatField(blank=True, null=True, help_text="Media duration") 
    thumbnail = models.TextField(blank=True, null=True, help_text="Base64 thumnail")
    
     
    path = models.TextField()
    
     
    preview = models.TextField(blank=True, null=True, help_text="Base64 preview or URL")
    
     
    caption = models.TextField(blank=True, null=True)

    contact_phones = models.TextField(blank=True, null=True)
    contact_emails = models.TextField(blank=True, null=True)
    contact_org = models.TextField(blank=True, null=True)
    contact_name = models.TextField(blank=True, null=True)
    

    class Meta:
         
        db_table = 'whatsapp_media'
        verbose_name = 'WhatsApp Media'
        verbose_name_plural = 'WhatsApp Media'

    def __str__(self):
        return f"{self.id} ({self.name}) {{self.size}} {self.type} {{self.path}} {{self.preview}} {{self.caption}} {{self.duration}} {{self.thumbnail}} {{self.contact_phones}}  {{self.contact_emails}} {{self.contact_org}} {{self.contact_name}}"