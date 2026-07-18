# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from core.responses import response
import core.logger as logger
import traceback
from WhatsPanel.services.userservice import userservice
from WhatsPanel.serializer.UserSerializer import *
from WhatsPanel.serializer.WhatsAppUserRegistrationSerializer import *
from WhatsPanel.serializer.AuthSerializer import *
from django.contrib.auth import get_user_model
from core.utils import success_response, custom_exception_handler, error_response


class UsersViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    def health_check(self, request):
        return HttpResponse("OK")
    def Getuser(self, request):
        try:
            userservicecls = userservice()
            GetUserresponse = userservicecls.GetUser(request)
            if ('error' in GetUserresponse and GetUserresponse['error']):
                return error_response(GetUserresponse)
            return success_response(GetUserresponse)
        except Exception as e:
            
            logger.app_logs("EXCEPTION", "Failed to get user data ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
            #return custom_exception_handler(e)
            

    def Createuser(self, request):
        try:

            serializer = updateUserSerializer(
                data=request.data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response(
                data=serializer.data,
                message='Profile created successfully.',
            )

            # userservicecls = userservice()
            # GetUserresponse = userservicecls.GetUser(request)
            # if ('error' in GetUserresponse and GetUserresponse['error']):
            #     return error_response(GetUserresponse)
            # return success_response(GetUserresponse)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to create user ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
            

    def Updateuser(self, request, id):
        try:
            #user_id=request.query_params.get('id', 0)
            instance = WhatsAppUser.objects.get(id=id)
            serializer = updateUserSerializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return success_response(
                data=updateUserSerializer(instance).data,
                message='Profile updated successfully.',
            )
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to update user ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
            
    
    def Deleteuser(self, request, id):
        try:
           
            user = WhatsAppUser.objects.get(id=id)
            if user.delete():
                return success_response(
                    message="User deleted successfully."
                )
            else:
                return error_response(
                    message="User not found."
                )

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to update user ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
            
    
    
    def PostFile(self, request):
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                file = serializer.validated_data['file']
                chat_id = serializer.validated_data['chat_id']

                # Do something (e.g., create user)
                return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
                # userservicecls = userservice()
                # GetUserresponse = userservicecls.PostFile(request)
                
                # return GetUserresponse
            else:
                return response(data = serializer.errors, status_code = status.HTTP_400_BAD_REQUEST, error=1)
        except ValidationError as e:
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to get item data ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})

    def refreshToken(self, request):
        try:

            userservicecls = userservice()
            GetUserresponse = userservicecls.refreshToken(request)

            if ('error' in GetUserresponse and GetUserresponse['error']):
                return error_response(GetUserresponse)
            return success_response(GetUserresponse)
    
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to refresh token ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        

    def subcribeApps(self, request):
        try:

            userservicecls = userservice()
            GetUserresponse = userservicecls.subcribeApps(request)

            if ('error' in GetUserresponse and GetUserresponse['error']):
                return error_response(GetUserresponse)
            return success_response(GetUserresponse)

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to subcribeApps ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def subscribeCallBackUrl(self, request):
        try:

            userservicecls = userservice()
            GetUserresponse = userservicecls.subscribeCallBackUrl(request)

            if ('error' in GetUserresponse and GetUserresponse['error']):
                return error_response(GetUserresponse)
            return success_response(GetUserresponse)

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to subscribeCallBackUrl ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        

    
    
