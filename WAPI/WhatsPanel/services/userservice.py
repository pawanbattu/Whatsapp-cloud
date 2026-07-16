from rest_framework.response import Response
from WhatsPanel.queries import *
import core.logger as logger
from core.whatsapp_caller import WhatsApp
import traceback
import json
import asyncio
from django.db import connections
from core.responses import response
from django.core.files.storage import FileSystemStorage
from rest_framework import status
from django.conf import settings
import os
import uuid
from core.utils import success_response, custom_exception_handler, error_response

class userservice():
    def __init__(self):
        pass

    def GetUser(self, request):
        try:
            getallusers = int(request.query_params.get('alluser', 0))
            usersResponse = {'data' :[], 'error' : True}
            obj = WhatsAppAdminUser.objects.filter(owner=request.user).first()
        
            WhatsAppUserQueryModel = WhatsAppUserQuery()
            users = WhatsAppUserQueryModel.getUser(getallusers, obj.id.hex)

            if ('error' in users and users['error']):
                logger.app_logs("ERROR", "Failed to users data ", {"error": users['error'], "response": users})       
            
            if users.get('data'):
                if getallusers == 1:
                    for usr in users['data']:
                        usersResponse['data'].append({'id': usr.id, 'phone_number': usr.phone_number, 'wa_id': usr.wa_id, 'whatsapp_name': usr.whatsapp_name, 'is_opted_in': usr.is_opted_in, 'opted_in_at': usr.opted_in_at, 'is_valid_whatsapp_number': usr.is_valid_whatsapp_number, 'last_user_message_at': usr.last_user_message_at, 'avatar': usr.avatar, 'created_at' : usr.created_at, 'updated_at' : usr.updated_at})
                    usersResponse['error'] = False
                else:
                    for usr in users['data']:
                        usersResponse['data'].append({'id': usr.id, 'name': usr.name, 'status': 'online', 'phone' : usr.phone_number, 'avatar': usr.avatar, 'lastSeen': usr.lastSeen, 'isCurrent': 1 if usr.id == 1 else 0})
                    usersResponse['error'] = False

            return usersResponse

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to get item data ", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})   
            return custom_exception_handler(e)
        
    def UpdateUser(self, request):
        try:
            getallusers = int(request.query_params.get('alluser', 0))
            usersResponse = {'data' :[], 'error' : True}
            WhatsAppUserQueryModel = WhatsAppUserQuery()
            users = WhatsAppUserQueryModel.getUser(getallusers)

            if ('error' in users and users['error']):
                logger.app_logs("ERROR", "Failed to users data ", {"error": users['error'], "response": {users}})       
            
            if users.get('data'):
                if getallusers == 1:
                    for usr in users['data']:
                        usersResponse['data'].append({'id': usr.id, 'phone_number': usr.phone_number, 'wa_id': usr.wa_id, 'whatsapp_name': usr.whatsapp_name, 'is_opted_in': usr.is_opted_in, 'opted_in_at': usr.opted_in_at, 'is_valid_whatsapp_number': usr.is_valid_whatsapp_number, 'last_user_message_at': usr.last_user_message_at, 'avatar': usr.avatar, 'created_at' : usr.created_at, 'updated_at' : usr.updated_at})
                    usersResponse['error'] = False
                else:
                    for usr in users['data']:
                        usersResponse['data'].append({'id': usr.id, 'name': usr.name, 'status': 'online', 'avatar': usr.avatar, 'lastSeen': usr.lastSeen, 'isCurrent': 1 if usr.id == 1 else 0})
                    usersResponse['error'] = False

            return usersResponse

        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to get item data ", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})   
            return custom_exception_handler(e)
        
    
    def refreshToken(self, request):
        try:
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in data and data['error']):
                return data
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            if (not (data['data'].app_id or data['data'].app_secret or data['data'].access_token)):
                logger.app_logs("ERROR", "app_id or app_secret or access_token is empty ")       
                return {'data' :["app_id or app_secret or access_token is empty "], 'error' : True}
            

            refresh_accesstoken = asyncio.run(WhatsApps.refresh_accesstoken(data))

            if ('error' in refresh_accesstoken and refresh_accesstoken['error']):
                logger.app_logs("ERROR", "Failed to refresh token", {"error": refresh_accesstoken['error'], "response": refresh_accesstoken})       
                
                return refresh_accesstoken
            
            token = refresh_accesstoken.get('data', {}).get('access_token')            
            if (not token):
                return {'data' :["Empty token recieved"], 'error' : True}
            

            WhatsAppUserQueryModel = WhatsAppAdminUserQuery()
            saveUserData = WhatsAppUserQueryModel.saveUserData(request.user, token)
            if ('error' in saveUserData and saveUserData['error']):
                logger.app_logs("ERROR", "Failed to save refresh token", {"error": saveUserData['error'], "response": saveUserData})       
                
                return saveUserData
            
            return {'data' : refresh_accesstoken, 'error' : False}
        
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to refresh whatsapp access token data ", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})   
            return custom_exception_handler(e, {'view': self, 'request': request})

    def PostFile(self, request):
        try:
            
            file_obj = request.FILES.get('file')
            if not file_obj:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

            chat_id = request.data.get('chat_id', 'general')

            # Create a subfolder dynamically (like whatsapp/{chat_id}/)
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'whatsapp', str(chat_id))
            os.makedirs(upload_dir, exist_ok=True)

            # Save file in the folder
            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(file_obj.name, file_obj)
            file_url = fs.url(os.path.join('uploads/whatsapp', str(chat_id), filename))

            # Build absolute URL
            absolute_url = request.build_absolute_uri(file_url)
            
            return response("Done upload")
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to get item data ", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})    

    def subcribeApps(self, request):
        try:
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in data and data['error']):
                return data
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            if (not (data['data'].app_id or data['data'].app_secret or data['data'].access_token or data['data'].subscribed_fields)):
                logger.app_logs("ERROR", "app_id or app_secret or access_token is empty or subscribed_fields is empty")       
                return {'data' :["app_id or app_secret or access_token or subscribed_fields is empty "], 'error' : True}
            

            subscribeAppsRes = asyncio.run(WhatsApps.subscribeApps(data))

            if ('error' in subscribeAppsRes and subscribeAppsRes['error']):
                logger.app_logs("ERROR", "Failed to subscribeApps", {"error": subscribeAppsRes['error'], "response": subscribeAppsRes})       
                
                return subscribeAppsRes
            
            return {'data' : subscribeAppsRes, 'error' : False}
        
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to subscribeApps", {"error": str(traceback.format_exc()), "inputData": request.data})   
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def subscribeCallBackUrl(self, request):
        try:

            data = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in data and data['error']):
                return data
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            if (not (data['data'].app_id or data['data'].app_secret or data['data'].access_token or data['data'].webhook_verify_token or data['data'].domain)):
                logger.app_logs("ERROR", "app_id or app_secret or access_token is empty or webhook_verify_token is empty")       
                return {'data' :["app_id or app_secret or access_token or webhook_verify_token is empty "], 'error' : True}
            
            callback_url = f"{data['data'].domain}/api/v1/messages/receiveMessages/{data['data'].owner_id}/"
        
            refresh_accesstoken = asyncio.run(WhatsApps.subscribeCallBackUrl(data, callback_url))

            if ('error' in refresh_accesstoken and refresh_accesstoken['error']):
                logger.app_logs("ERROR", "Failed to subscribe to CallBackUrl", {"error": refresh_accesstoken['error'], "response": refresh_accesstoken})       
                
                return refresh_accesstoken
            
        
            return {'data' : refresh_accesstoken, 'error' : False}
        
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to subscribe to CallBackUrl", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})   
            return custom_exception_handler(e, {'view': self, 'request': request})
    

        