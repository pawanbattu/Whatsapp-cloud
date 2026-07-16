from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from WhatsPanel.models import *

User = get_user_model()

class WhatsAppUserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    project_name = serializers.CharField(
        write_only=True, 
        required=False, 
        help_text="The name of their new WhatsApp workspace."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'project_name']

    @transaction.atomic
    def create(self, validated_data):

        password = validated_data.pop('password')
        project_name = validated_data.pop('project_name', None)
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        default_name = project_name if project_name else f"{user.username}'s Project"
        
        WhatsAppAdminUser.objects.create(
            owner=user,
            name=default_name,
        )

        return user