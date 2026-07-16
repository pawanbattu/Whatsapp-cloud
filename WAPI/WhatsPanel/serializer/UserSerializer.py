# app/serializers.py
from rest_framework import serializers
from WhatsPanel.models.WhatsAppUser import *
import re

class UserSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    chat_id = serializers.IntegerField(required=True)
    
class updateUserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField()
    class Meta:
        model = WhatsAppUser
        fields = [
            'id', 'phone_number', 'wa_id', 'whatsapp_name', 
            'is_opted_in', 'is_valid_whatsapp_number', 
            'avatar', 'created_at', 'updated_at',
        ]

        extra_kwargs = {
            'whatsapp_name': {'allow_blank': True, 'required': False},
            'is_opted_in': {'required': False},
            'is_valid_whatsapp_number': {'required': False},
            'avatar': {'allow_blank': True, 'required': False},
        }    

    def validate_phone_number(self, value):
        """Phone must be E.164 without the leading +  e.g. 919876543210"""
        if not re.fullmatch(r"[1-9]\d{6,14}", value):
            raise serializers.ValidationError(
                "Must be a valid E.164 phone number (digits only, no +, 7-15 chars)."
            )
        return value

    def update(self, instance, validated_data):    
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
      
    def create(self, validated_data):
        request = self.context.get('request')
        admin_user = WhatsAppAdminUser.objects.filter(owner=request.user).first()
        
        if admin_user:
            validated_data['whatsapp_admin'] = admin_user 
            
            
        return WhatsAppUser.objects.create(**validated_data)

