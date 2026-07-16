from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from WhatsPanel.models.WhatsAppAdminUser import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re
from django.utils import timezone
from datetime import datetime
from django.utils.dateparse import parse_datetime

class SubmitTemplateserializer(serializers.Serializer):
    template_data = serializers.JSONField(required=True)

    def validate_template_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("template_data must be a dictionary")

        if "name" not in value:
            raise serializers.ValidationError("Missing 'name' key in template_data")

        return value






#----------------Send template serializer--------------------------#

def validate_whatsapp_variable_format(text):
    """Warn if text contains obvious placeholder strings that are NOT {{n}} variables."""
    suspicious = re.findall(r"#\w+|(?<!\{)\b[a-z]{3,}\b(?!\})", text)
    
    has_vars = bool(re.search(r"\{\{\d+\}\}", text))
    if not has_vars and len(text.split()) < 30:
        pass
    return text


# ──────────────────────────────────────────
# Header
# ──────────────────────────────────────────

class HeaderSerializer(serializers.Serializer):
    HEADER_TYPES = ["TEXT", "IMAGE", "VIDEO", "DOCUMENT", "LOCATION"]

    type     = serializers.ChoiceField(choices=HEADER_TYPES)
    text     = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    media    = serializers.URLField(required=False, allow_null=True)       
    mediaUrl = serializers.URLField(required=False, allow_null=True)       
    example  = serializers.DictField(required=False)

    def validate(self, attrs):
        header_type = attrs.get("type")

        if header_type == "TEXT" and not attrs.get("text"):
            raise serializers.ValidationError({"text": "Required when header type is TEXT."})

        if header_type in ["IMAGE", "VIDEO", "DOCUMENT"]:
            if not attrs.get("media") and not attrs.get("mediaUrl"):
                raise serializers.ValidationError(
                    {"media": f"media or mediaUrl is required when header type is {header_type}."}
                )

        return attrs


# ──────────────────────────────────────────
# Buttons
# ──────────────────────────────────────────

class QuickReplySerializer(serializers.Serializer):
    text = serializers.CharField(max_length=25)  # WA limit: 25 chars


class CTAButtonSerializer(serializers.Serializer):
    BUTTON_TYPES = ["URL", "PHONE_NUMBER"]

    type = serializers.ChoiceField(choices=BUTTON_TYPES)
    text = serializers.CharField(max_length=25)
    url = serializers.URLField(required=False)
    phone_number = serializers.CharField(required=False)
    payload = serializers.CharField(required=False)  

    def validate(self, attrs):
        if attrs.get("type") == "URL" and not attrs.get("url"):
            raise serializers.ValidationError(
                {"url": "Required when button type is URL."}
            )
        if attrs.get("type") == "PHONE_NUMBER" and not attrs.get("phone_number"):
            raise serializers.ValidationError(
                {"phone_number": "Required when button type is PHONE_NUMBER."}
            )
        return attrs


class ButtonsSerializer(serializers.Serializer):
    quickReplies = QuickReplySerializer(many=True, required=False, default=list)
    cta = CTAButtonSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        quick_replies = attrs.get("quickReplies", [])
        cta_buttons = attrs.get("cta", [])
        
        # 2. Check Specific Limits
        if len(quick_replies) > 10:
            raise serializers.ValidationError("Maximum 10 Quick Replies allowed.")
        
        if len(cta_buttons) > 2:
            raise serializers.ValidationError("Maximum 2 CTA buttons allowed.")

        return attrs


# ──────────────────────────────────────────
# Components (inner template definition)
# ──────────────────────────────────────────

VALID_CATEGORIES = ["MARKETING", "UTILITY", "AUTHENTICATION"]


class ComponentsSerializer(serializers.Serializer):
    name = serializers.RegexField(
        r"^[a-z0-9_]+$",
        max_length=512,
        error_messages={
            "invalid": "Template name must be lowercase letters, numbers, and underscores only."
        },
    )
    category = serializers.ChoiceField(
        choices=VALID_CATEGORIES,
        error_messages={
            "invalid_choice": (
                f"'{'{value}'}' is not a valid category. "
                f"Allowed values: {VALID_CATEGORIES}. "
                "'TRANSACTIONAL' was deprecated by Meta."
            )
        },
    )
    language = serializers.RegexField(
        r"^[a-z]{2,3}(_[A-Z]{2})?$",
        error_messages={"invalid": "Language must follow BCP-47 format e.g. en_US, en, hi."},
    )
    header = HeaderSerializer(required=False)
    body = serializers.CharField(max_length=1024)
    footer = serializers.CharField(max_length=60, required=False, allow_blank=True)
    buttons = ButtonsSerializer(required=False)

    # Optional metadata fields
    businessName = serializers.CharField(max_length=255, required=False)
    sender = serializers.CharField(max_length=255, required=False)
    templateId = serializers.CharField(required=False)
    templateName = serializers.CharField(required=False)

    whatsappApiComponents = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_null=True
    )

    def validate_body(self, value):
        """
        Variables in body must use {{n}} notation.
        If the body contains obvious un-bracketed placeholders, raise a warning error.
        """
        bad_placeholders = re.findall(r"#\w+", value)
        if bad_placeholders:
            raise serializers.ValidationError(
                f"Body contains invalid placeholders {bad_placeholders}. "
                "Use {{1}}, {{2}}, ... format for dynamic values."
            )
        return value

    def validate_footer(self, value):
        if value and len(value) > 60:
            raise serializers.ValidationError("Footer must not exceed 60 characters.")
        return value


# ──────────────────────────────────────────
# Root / Envelope Serializer
# ──────────────────────────────────────────

class WhatsAppTemplateMessageSerializer(serializers.Serializer):
    """
    Top-level serializer for a WhatsApp template message send request.
    Maps to the JSON payload your frontend / service sends to the API.
    """

    to = serializers.CharField()
    templateName = serializers.RegexField(
        r"^[a-z0-9_]+$",
        max_length=512,
        error_messages={"invalid": "templateName must be lowercase, numbers, and underscores only."},
    )
    templateId = serializers.CharField(required=False)
    language = serializers.RegexField(
        r"^[a-z]{2,3}(_[A-Z]{2})?$",
        error_messages={"invalid": "Language must follow BCP-47 e.g. en_US, hi, pt_BR."},
    )
    components = ComponentsSerializer()

    def validate(self, attrs):
        """Cross-field: root templateName must match components.name."""
        root_name = attrs.get("templateName")
        inner_name = attrs.get("components", {}).get("name") if isinstance(attrs.get("components"), dict) else None
        # After nested serializer runs, components is already a validated dict
        if hasattr(attrs.get("components"), "get"):
            inner_name = attrs["components"].get("name")

        if root_name and inner_name and root_name != inner_name:
            raise serializers.ValidationError(
                {"templateName": "Root templateName must match components.name."}
            )
        return attrs

#----------------Send template serializer--------------------------#    

class SchdeuleTemplateMessageSerializer(serializers.Serializer):
    """
    Top-level serializer for a WhatsApp template message send request.
    Maps to the JSON payload your frontend / service sends to the API.
    """

    to = serializers.ListField(child=serializers.IntegerField(min_value=1), required=True)
    scheduled_at = serializers.CharField(allow_blank=False, required=True)
    repeat = serializers.CharField(required=False, allow_null=True)

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

    templateName = serializers.RegexField(
        r"^[a-z0-9_]+$",
        max_length=512,
        error_messages={"invalid": "templateName must be lowercase, numbers, and underscores only."},
    )
    templateId = serializers.CharField(required=False)
    language = serializers.RegexField(
        r"^[a-z]{2,3}(_[A-Z]{2})?$",
        error_messages={"invalid": "Language must follow BCP-47 e.g. en_US, hi, pt_BR."},
    )
    components = ComponentsSerializer()

    def validate(self, attrs):
        """Cross-field: root templateName must match components.name."""
        root_name = attrs.get("templateName")
        inner_name = attrs.get("components", {}).get("name") if isinstance(attrs.get("components"), dict) else None
        # After nested serializer runs, components is already a validated dict
        if hasattr(attrs.get("components"), "get"):
            inner_name = attrs["components"].get("name")

        if root_name and inner_name and root_name != inner_name:
            raise serializers.ValidationError(
                {"templateName": "Root templateName must match components.name."}
            )
        return attrs

