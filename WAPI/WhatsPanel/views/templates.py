# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
# from .models import Post, Comment, User
# from .serializers import PostSerializer, CommentSerializer, UserSerializer
from WhatsPanel.models.sqlite_models import *
from core.responses import response
import core.logger as logger
import traceback
from WhatsPanel.services.templateservice import templateservice
from WhatsPanel.serializer.TemplateSerializer import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from core.utils import success_response, custom_exception_handler, error_response


class TemplatesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def Sendtemplate(self, request):
        try:
            
            serializer = WhatsAppTemplateMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            templateservicecls = templateservice()
            templateserviceclsresponse = templateservicecls.Sendtemplate(request)
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.app_logs("ERROR", "Failed to send template ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})

    def Savetemplate(self, request):
        try:
                
            templateservicecls = templateservice()
            templateserviceclsresponse = templateservicecls.Savetemplate(request)
            
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to save template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : templateserviceclsresponse})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def Submittemplate(self, request):
        try:
            serializer = SubmitTemplateserializer(
            request.user, data=request.data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            templateservicecls = templateservice()
            templateserviceclsresponse = templateservicecls.submitTemplate(request)
            
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to submit template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    
    def Gettemplates(self, request):
        try:
        
            templateservicecls = templateservice()
            from_db = int(request.query_params.get('from_db', 0))
            all_data = from_db = request.query_params.get('all_data', '')
            templateserviceclsresponse = templateservicecls.getTemplate(request, from_db, all_data)
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to save template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
    
    def Synctemplate(self, request):
        try:
        
            templateservicecls = templateservice()
            
            templateserviceclsresponse = templateservicecls.Synctemplate(request)
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to sync template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
        
        
    @action(methods=['delete'], detail=False, url_path='Deletetemplate/(?P<template_name>[^/.]+)')
    def Deletetemplate(self, request, template_name=None):
        try:
            templateservicecls = templateservice()
            templateserviceclsresponse = templateservicecls.deleteTemplate(request, template_name)
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to delete template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    @action(methods=['post'], detail=False, url_path='Edittemplate/(?P<template_id>[^/.]+)')
    def Edittemplate(self, request, template_id=None):
        try:
            serializer = SubmitTemplateserializer(
            request.user, data=request.data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            templateservicecls = templateservice()
            templateserviceclsresponse = templateservicecls.editTemplate(request, template_id)
            
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to edit template data ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def Scheduletemplate(self, request):
        try:
            serializer = SchdeuleTemplateMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            templateservicecls = templateservice()
            
            templateserviceclsresponse = templateservicecls.scheduleTemplate(request, serializer.validated_data)
            if (isinstance(templateserviceclsresponse, dict) and templateserviceclsresponse.get('error')):
                return error_response(templateserviceclsresponse)
            return success_response(templateserviceclsresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("ERROR", "Failed to schedule template  ", {"error": str(traceback.format_exc()), "inputData": request, 'response' : e})
            return custom_exception_handler(e, {'view': self, 'request': request})
