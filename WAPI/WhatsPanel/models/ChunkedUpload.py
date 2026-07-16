from django.db import models
from django.utils import timezone

class ChunkedUpload(models.Model):
    upload_id = models.CharField(max_length=100, unique=True)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    chunk_size = models.IntegerField()
    total_chunks = models.IntegerField()
    uploaded_chunks = models.IntegerField(default=0)
    chat_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.filename} ({self.upload_id})"