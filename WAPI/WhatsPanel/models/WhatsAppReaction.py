from django.db import models
from .WhatsAppAdminUser import *


class WhatsAppReaction(models.Model):
    message = models.IntegerField()
    user = models.IntegerField()
    emoji = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.message} \
                {self.user} \
                {self.emoji}"

    def __str__(self):
        return f"{self.id} {self.emoji} (Message: {self.message_id}, User: {self.user_id})"