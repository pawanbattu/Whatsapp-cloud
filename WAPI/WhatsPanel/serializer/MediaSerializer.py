from rest_framework import serializers
from WhatsPanel.models import *
import re

def sanitize_filename(filename: str) -> str:
    # Get extension
    if '.' in filename:
        name, ext = filename.rsplit('.', 1)
    else:
        name, ext = filename, ''

    name = name.replace(' ', '_')
    name = re.sub(r'[^\w\-]', '', name)
    
    return f"{name}.{ext}" if ext else name


class StartUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChunkedUpload
        fields = [
            'upload_id', 'filename', 'file_size', 'file_type',
            'chunk_size', 'total_chunks', 'chat_id'
        ]

    def validate_filename(self, value):
        return sanitize_filename(value)


class UploadChunkSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    chunk_index = serializers.IntegerField()
    total_chunks = serializers.IntegerField()
    chunk = serializers.FileField()
    filename = serializers.CharField()

    def validate_filename(self, value):
        return sanitize_filename(value)


class CompleteUploadSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    filename = serializers.CharField()

    def validate_filename(self, value):
        return sanitize_filename(value)


class CancelUploadSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
