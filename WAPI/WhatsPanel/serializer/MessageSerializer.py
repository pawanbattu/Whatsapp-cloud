from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from django.utils.dateparse import parse_datetime
from .TemplateSerializer import *
from WhatsPanel.models import *


# ──────────────────────────────────────────
# WhatsApp Media Rules
# ──────────────────────────────────────────

WHATSAPP_MEDIA_RULES = {
    "image": {
        "max_size_mb": 5,
        "allowed_types": {
            "image/jpeg",
            "image/png",
            "image/webp",
        },
    },
    "audio": {
        "max_size_mb": 16,
        "allowed_types": {
            "audio/mpeg",       # MP3
            "audio/ogg",        # OGG (Opus)
            "audio/aac",        # AAC
            "audio/mp4",        # MP4 audio
            "audio/amr",        # AMR
        },
    },
    "video": {
        "max_size_mb": 16,
        "allowed_types": {
            "video/mp4",        # MP4 (H.264 + AAC only)
            "video/3gpp",       # 3GPP
        },
    },
    "document": {
        "max_size_mb": 100,
        "allowed_types": None,  # None = all MIME types allowed
    },
}


# ──────────────────────────────────────────
# Helper: parse size string like "4.21 MB" → float MB
# ──────────────────────────────────────────

def parse_size_mb(size_str: str) -> float:
    """
    Parses size strings like '4.21 MB', '512 KB', '1.2 GB' into MB (float).
    Raises ValueError if format is unrecognized.
    """
    size_str = size_str.strip()
    parts = size_str.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid size format: '{size_str}'. Expected e.g. '4.21 MB'")

    value, unit = parts
    value = float(value)
    unit = unit.upper()

    conversion = {
        "B":  value / (1024 ** 2),
        "KB": value / 1024,
        "MB": value,
        "GB": value * 1024,
    }

    if unit not in conversion:
        raise ValueError(f"Unknown size unit: '{unit}'. Expected B, KB, MB, or GB.")

    return conversion[unit]


# ──────────────────────────────────────────
# Mixin: validates type and size against WhatsApp rules
# ──────────────────────────────────────────

class WhatsAppMediaValidationMixin:
    """
    Add to any file serializer to enforce WhatsApp type + size rules.
    Subclass must set `media_category` to one of: image, audio, video, document.
    """
    media_category: str = None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        rules = WHATSAPP_MEDIA_RULES.get(self.media_category)
        if not rules:
            raise serializers.ValidationError(
                f"No WhatsApp rules defined for media category: '{self.media_category}'"
            )

        # ── Validate MIME type ──
        mime_type = attrs.get("type", "").lower().strip()
        allowed_types = rules["allowed_types"]

        if allowed_types is not None:
            # Normalize: strip codec suffix for matching e.g. "audio/ogg; codecs=opus"
            mime_base = mime_type.split(";")[0].strip()
            if mime_base not in allowed_types:
                raise serializers.ValidationError({
                    "type": (
                        f"'{mime_type}' is not supported for {self.media_category}. "
                        f"Allowed types: {', '.join(sorted(allowed_types))}"
                    )
                })

        # ── Validate file size ──
        size_str = attrs.get("size", "")
        try:
            size_mb = parse_size_mb(size_str)
        except ValueError as e:
            raise serializers.ValidationError({"size": str(e)})

        max_mb = rules["max_size_mb"]
        if size_mb > max_mb:
            raise serializers.ValidationError({
                "size": (
                    f"File size {size_str} exceeds the {max_mb} MB limit "
                    f"for {self.media_category} messages."
                )
            })

        return attrs


# ──────────────────────────────────────────
# File Serializers
# ──────────────────────────────────────────

class ImageFileSerializer(WhatsAppMediaValidationMixin, serializers.Serializer):
    media_category = "image"

    name    = serializers.CharField()
    size    = serializers.CharField()
    type    = serializers.CharField()
    path    = serializers.CharField()
    preview = serializers.CharField(allow_null=True, required=False)
    caption = serializers.CharField(allow_blank=True, required=False, default="")
    thumbnail = serializers.CharField(allow_null=True, required=False)



class VideoFileSerializer(WhatsAppMediaValidationMixin, serializers.Serializer):
    media_category = "video"

    name    = serializers.CharField()
    size    = serializers.CharField()
    type    = serializers.CharField()
    path    = serializers.CharField()
    preview = serializers.CharField(allow_null=True, required=False)
    caption = serializers.CharField(allow_blank=True, required=False, default="")
    thumbnail = serializers.CharField(allow_null=True, required=False)
    duration = serializers.CharField(allow_null=True, required=False)


class AudioFileSerializer(WhatsAppMediaValidationMixin, serializers.Serializer):
    media_category = "audio"

    name    = serializers.CharField()
    size    = serializers.CharField()
    type    = serializers.CharField()
    path    = serializers.CharField()
    preview = serializers.CharField(allow_null=True, required=False)
    thumbnail = serializers.CharField(allow_null=True, required=False)
    duration = serializers.CharField(allow_null=True, required=False)


class DocumentFileSerializer(WhatsAppMediaValidationMixin, serializers.Serializer):
    media_category = "document"

    name     = serializers.CharField()
    size     = serializers.CharField()
    type     = serializers.CharField()
    path     = serializers.CharField()
    preview  = serializers.CharField(allow_null=True, required=False)
    caption  = serializers.CharField(allow_blank=True, required=False, default="")
    filename = serializers.CharField(allow_blank=True, required=False, default="")
    thumbnail = serializers.CharField(allow_null=True, required=False)
    # WhatsApp shows this as the document display name in chat


class LocationFileSerializer(serializers.Serializer):
    name    = serializers.CharField(default="Location")
    size    = serializers.CharField(default="Location")
    type    = serializers.CharField(default="location")
    preview = serializers.CharField(allow_null=True, required=False)
    address = serializers.CharField()
    coordinates = serializers.DictField(
        child=serializers.FloatField()
    )  
    caption = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_coordinates(self, value):
        if "lat" not in value or "lng" not in value:
            raise serializers.ValidationError(
                "coordinates must contain both 'lat' and 'lng' keys."
            )
        if not (-90 <= value["lat"] <= 90):
            raise serializers.ValidationError("lat must be between -90 and 90.")
        if not (-180 <= value["lng"] <= 180):
            raise serializers.ValidationError("lng must be between -180 and 180.")
        return value
    
class ContactNameSerializer(serializers.Serializer):
    formatted_name = serializers.CharField()
    first_name     = serializers.CharField(allow_blank=True, required=False, default="")
    last_name      = serializers.CharField(allow_blank=True, required=False, default="")


class ContactPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField()
    type  = serializers.CharField(allow_blank=True, required=False, default="WORK")
    wa_id = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_phone(self, value):
        """
        Validates and formats the phone number as per WhatsApp Cloud API rules.
        """
        clean_phone = re.sub(r'[\s\-\(\)]', '', str(value))
        
        if not re.match(r'^\+?[1-9]\d{6,14}$', clean_phone):
            raise serializers.ValidationError(
                "Phone number must be a valid E.164 format (e.g., '14155551234')."
            )
        return clean_phone.replace('+', '')


class ContactEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    type  = serializers.CharField(allow_blank=True, required=False, default="WORK")


class ContactDetailSerializer(serializers.Serializer):
    name   = ContactNameSerializer()
    phones = serializers.ListField(
        child=ContactPhoneSerializer(), allow_empty=True, required=False
    )
    emails = serializers.ListField(
        child=ContactEmailSerializer(), allow_empty=True, required=False
    )


class ContactFileSerializer(serializers.Serializer):
    name    = serializers.CharField(default="")
    size    = serializers.CharField(default="")
    type    = serializers.CharField(default="")
    preview = serializers.CharField(allow_null=True, required=False)
    caption = serializers.CharField(allow_blank=True, required=False, default="")
    contact = ContactDetailSerializer()
    


# ──────────────────────────────────────────
# Master message serializer
# ──────────────────────────────────────────

FILE_SERIALIZER_MAP = {
    "image":    ImageFileSerializer,
    "video":    VideoFileSerializer,
    "audio":    AudioFileSerializer,
    "document": DocumentFileSerializer,
    "location": LocationFileSerializer,
    "contact":  ContactFileSerializer, 
}

class MessageSerializer(serializers.Serializer):
    # to      = serializers.PrimaryKeyRelatedField(
    #     queryset=WhatsAppUser.objects.all()
    # )
    to      = serializers.IntegerField(
        allow_null=False, required=True
    )
    type    = serializers.ChoiceField(
        choices=["text", "image", "video", "audio", "document", "location", "contact"]  
    )
    text    = serializers.CharField(allow_blank=True, required=False, default="")
    file    = serializers.DictField(allow_null=True, required=False, default=None)
    replyTo = serializers.CharField(
        allow_null=True, required=False, default=None
    )
    replyToWamid = serializers.CharField(allow_null=True, allow_blank=True, required=False, default="")

    def validate(self, attrs):
        msg_type = attrs.get("type")
        file_data = attrs.get("file")

        # ── Text type ──
        if msg_type == "text":
            text = attrs.get("text", "")
            if not text or not text.strip():
                raise serializers.ValidationError(
                    {"text": "Text message cannot be empty."}
                )
            if len(text) > 4096:
                raise serializers.ValidationError(
                    {"text": f"Text message exceeds the 4096 character limit (got {len(text)})."}
                )
            attrs["file"] = None   # force null for text type
            return attrs

        # ── Media/Location types ──
        if not file_data:
            raise serializers.ValidationError(
                {"file": f"file is required for type '{msg_type}'."}
            )

        file_serializer_class = FILE_SERIALIZER_MAP.get(msg_type)
        if not file_serializer_class:
            raise serializers.ValidationError(
                {"type": f"Unsupported message type: {msg_type}"}
            )

        file_serializer = file_serializer_class(data=file_data)
        if not file_serializer.is_valid():
            raise serializers.ValidationError({"file": file_serializer.errors})

        attrs["file"] = file_serializer.validated_data
        return attrs
    
    def validate_replyToWamid(self, value):
        if value:
            if not WhatsAppMessage.objects.filter(wamid=value).exists():
                raise serializers.ValidationError("The provided replyToWamid does not exist in the database.")
        
        return value
    

class ScheduleMessageSerializer(serializers.Serializer):

    to = serializers.ListField(child=serializers.IntegerField(min_value=1), required=True)

    type    = serializers.ChoiceField(
        choices=["text", "image", "video", "audio", "document", "location", 'template']  
    )
    text    = serializers.CharField(allow_blank=True, required=False, default="")
    file    = serializers.DictField(allow_null=True, required=False, default=None)
  
    scheduled_at = serializers.CharField(allow_blank=False, required=True)
    def validate_scheduled_at(self, value):
        # 1. If value is still a string (though DRF usually converts it)
        if isinstance(value, str):
            value = parse_datetime(value)
            if not value:
                raise serializers.ValidationError("Invalid date format.")

        # 2. Handle timezone "awareness" 
        # Ensure we are comparing UTC to UTC or aware to aware
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.utc)

        # 3. Perform the comparison
        if value <= timezone.now():
            raise serializers.ValidationError("The scheduled time must be in the future.")

        return value
    repeat = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        msg_type = attrs.get("type")

        # ── Text type ──
        if msg_type == "text":
            text = attrs.get("text", "")
            if not text or not text.strip():
                raise serializers.ValidationError({"text": "Text message cannot be empty."})
            if len(text) > 4096:
                raise serializers.ValidationError(
                    {"text": f"Text message exceeds the 4096 character limit (got {len(text)})."}
                )
            attrs["file"] = None
            return attrs

        # ── Template type ──
        # if msg_type == "template":
        #     
        #  
        #     template_serializer = WhatsAppTemplateMessageSerializer(data=self.initial_data)
            
        #     if not template_serializer.is_valid():
        #         # Raise the exact errors caught by the template serializer
        #         raise serializers.ValidationError(template_serializer.errors)
            
        #     # Merge the validated template data back into our current attrs
        #     attrs.update(template_serializer.validated_data)
        #     attrs["file"] = None # Force null for file
        #     attrs["text"] = ""   # Force empty for text
        #     return attrs

        # ── Media/Location types ──
        file_data = attrs.get("file")
        if not file_data:
            raise serializers.ValidationError(
                {"file": f"file is required for type '{msg_type}'."}
            )

        file_serializer_class = FILE_SERIALIZER_MAP.get(msg_type)
        if not file_serializer_class:
            raise serializers.ValidationError(
                {"type": f"Unsupported message type: {msg_type}"}
            )

        file_serializer = file_serializer_class(data=file_data)
        if not file_serializer.is_valid():
            raise serializers.ValidationError({"file": file_serializer.errors})

        attrs["file"] = file_serializer.validated_data

        return attrs
    
class ReactionDetailSerializer(serializers.Serializer):
    message_id = serializers.CharField(
        required=True, 
        help_text="The WAMID of the message you are reacting to."
    )
    emoji = serializers.CharField(
        allow_blank=True, 
        required=True,
        help_text="The emoji to send, or an empty string to remove the reaction."
    )

    def validate_message_id(self, value):
        if not value.startswith("wamid."):
            raise serializers.ValidationError("Invalid message_id. It must start with 'wamid.'")
        return value

class WhatsAppReactionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[("reaction", "reaction")], default="reaction")
    to = serializers.IntegerField(allow_null=False, required=True)
    message_id = serializers.CharField(
        required=True, 
        help_text="The WAMID of the message you are reacting to."
    )
    emoji = serializers.CharField(
        allow_blank=True, 
        required=True,
        help_text="The emoji to send, or an empty string to remove the reaction."
    )

    def validate_message_id(self, value):
        if not value.startswith("wamid."):
            raise serializers.ValidationError("Invalid message_id. It must start with 'wamid.'")
        return value
    