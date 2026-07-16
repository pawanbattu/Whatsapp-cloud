import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import core.logger as logger
from core.tasks import process_whatsapp_webhook
from rest_framework.permissions import AllowAny
import traceback
from WhatsPanel.queries import *

#VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"

class ReceiveMessageView(APIView):
    permission_classes = [AllowAny]
    """
    Handles WhatsApp Webhook Verification and Event Receiving.
    """
    def get(self, request, admin_id):
        try:
            verify_token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")

            getUserData = WhatsAppAdminUserQuery.getUserData(admin_id)
            
            if ('error' in getUserData and getUserData['error']):
                logger.app_logs("ERROR", "Webhook Verification failed to get data from db", {"inputData": admin_id, "request": request, 'error': getUserData})
                return getUserData
            
            if verify_token == getUserData['data'].webhook_verify_token:
                return HttpResponse(challenge, content_type="text/plain", status=status.HTTP_200_OK)

            logger.app_logs("ERROR", "Webhook Verification failed", {"inputData": request})
            return Response({"error": "Invalid verification token"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed verify callback url", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    def post(self, request, admin_id):
        try:
            data = request.data
            
            process_whatsapp_webhook.delay(data)
            
            return Response("OK", status=status.HTTP_200_OK)
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed get message from whatsapp", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise