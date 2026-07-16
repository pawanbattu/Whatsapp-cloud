# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from WhatsPanel.models.sqlite_models import *
from core.responses import response
import core.logger as logger
import traceback
from WhatsPanel.services.messageservice import messageservice
from core.utils import success_response, custom_exception_handler, error_response
from WhatsPanel.serializer.MessageSerializer import *
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

class MessagesViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    def Getmessage(self, request):
        try:
            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.Getmessage(request)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get Message data ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    def Sendmessage(self, request):
        try:
            serializer = MessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.Sendmessage(request, serializer.validated_data)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.app_logs("ERROR", "Failed to send Message ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    
    def Schedulemessage(self, request):
        try:
            serializer = ScheduleMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.Schedulemessage(request, serializer.validated_data)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except DRFValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.app_logs("ERROR", "Failed to send Message ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    def Getconversations(self, request):
        try:
            conversation_id = request.query_params.get('conversation_id')
            offset          = int(request.GET.get('offset', 0))
            page_size       = int(request.GET.get('page_size', 50))

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.Getconversations(request, conversation_id, offset, page_size)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get Getconversations ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    def markMessageAsRead(self, request, user_id):
        try:

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.markMessageAsRead(request, user_id)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to save markMessageAsRead ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise
    
    def Sendreaction(self, request):
        try:
            serializer = WhatsAppReactionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.Sendreaction(request, serializer.validated_data)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.app_logs("ERROR", "Failed to Sendreaction ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise
    
    def GetSchedulemessage(self, request):
        try:
            offset          = int(request.GET.get('offset', 0))
            page_size       = int(request.GET.get('limit', 50))

            messageservicecls = messageservice()
            messageserviceclsresponse = messageservicecls.GetSchedulemessage(request, offset, page_size)

            if (isinstance(messageserviceclsresponse, dict) and messageserviceclsresponse.get('error')):
                return error_response(messageserviceclsresponse)
            
            return success_response(messageserviceclsresponse)
    
        except Exception as e:
            logger.app_logs("ERROR", "Failed to GetSchedulemessage ", {"error": str(traceback.format_exc()), "inputData": request.data})
            raise

    def DeleteSchedulemessage(self, request, id):
        try:
           
            ScheduledMessageModel = ScheduledMessage.objects.get(id=id)
            if ScheduledMessageModel.delete():
                return success_response(
                    message="ScheduledMessage deleted successfully."
                )
            else:
                return error_response(
                    message="ScheduledMessage not found."
                )

        except Exception as e:
            logger.app_logs("ERROR", "Failed to delete ScheduledMessage  ", {"error": str(traceback.format_exc()), "inputData": {request}})
            return custom_exception_handler(e, {'view': self, 'request': request})
    


    
        
    
    
