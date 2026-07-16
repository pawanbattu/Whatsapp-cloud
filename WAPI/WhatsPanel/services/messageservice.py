from rest_framework.response import Response
from WhatsPanel.queries import *
from WhatsPanel.models import *
from core.logger import app_logs
import traceback
import json
from django.db import connections
from core.responses import response
from core.whatsapp_caller import WhatsApp
import asyncio
import ast
from core.utils import success_response, custom_exception_handler

class messageservice():
    MESSAGE_TYPE_TEXT = 'text'
    MESSAGE_TYPE_IMAGE = 'image'
    MESSAGE_TYPE_VIDEO = 'video'
    MESSAGE_TYPE_AUDIO = 'audio'
    MESSAGE_TYPE_DOCUMENT = 'document'
    MESSAGE_TYPE_LOCATION = 'location'
    MESSAGE_TYPE_CONTACT = 'contact'

    def __init__(self):
        pass

    def Getmessage(self, request):
        messageResponse = {'data': [], 'error' : True}
        try:
            admin_config = WhatsAppAdminUser.objects.get(owner=request.user)
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            res = WhatsAppMessageQueryModel.get_conversations_json(admin_config)
           
            if ('error' in res and res['error']):
               logger.app_logs(
                    "ERROR",
                    "Failed to message data",
                    {"error": res['error'], "response": res}
                    )
               return messageResponse
            
            if ('data' in res and len(res['data']) > 0):
                conversations = res.get("data", {})
                
                for user_id, messages in conversations.items():
                    for msg in messages:
                        template_str = msg.get("template")
                        
                        if template_str and isinstance(template_str, str):
                            try:
                                msg["template"] = json.loads(template_str)
                            except json.JSONDecodeError:
                                try:
                                    # Fallback: Safely parse Python-style dict strings (works for single quotes)
                                    msg["template"] = ast.literal_eval(template_str)
                                except (ValueError, SyntaxError) as e:
                                    logger.app_logs(
                                        "WARNING",
                                        f"Failed to parse template data for message {msg.get('id')}",
                                        {"template_string": template_str, "error": str(e)}
                                    )
                                    msg["template"] = None 
                                    
            
            messageResponse = {'data': res['data'], 'error' : False}

            return messageResponse

        except Exception as e:
            app_logs("EXCEPTION", "Failed to message data ", {"error": str(traceback.format_exc()), "inputData": request})  
            return custom_exception_handler(e, {'view': self, 'request': request})
            

    def Sendmessage(self, request, data):
        try:
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in getUserData and getUserData['error']):
                return getUserData
            
            user_id = request.data.get('to', '')

            admin_config = WhatsAppUser.objects.get(id=user_id)
            if not admin_config:
                app_logs("ERROR", "User Not Found in DB", {"error": admin_config, "inputData": user_id})
                return {'data' : ["User Not Found in DB"], 'error' : True}
            
            WhatsApps = WhatsApp(getUserData['data'].access_token, getUserData['data'].phone_number_id, getUserData['data'].waba_id, getUserData['data'].templates_access_token)  
            
            components = request.data
            # Get the wamid. If it doesn't exist, it defaults to an empty string.
            replyMessageWamid = components.get('replyToWamid', "")

            allowed_type = [self.MESSAGE_TYPE_TEXT, self.MESSAGE_TYPE_AUDIO, self.MESSAGE_TYPE_VIDEO, self.MESSAGE_TYPE_IMAGE, self.MESSAGE_TYPE_DOCUMENT, self.MESSAGE_TYPE_LOCATION, self.MESSAGE_TYPE_CONTACT]
            message_type = components.get('type', {})
            resp = None
            
            if (message_type and message_type not in allowed_type):
                return {'data' : ['Not supported file type'], 'error' : True}
            
            if (message_type == self.MESSAGE_TYPE_TEXT):
                message = components.get('text', '')
                resp = asyncio.run(WhatsApps.send_message(message, admin_config.phone_number, reply_to=replyMessageWamid))
                
            elif (message_type == self.MESSAGE_TYPE_IMAGE):
                file = components.get('file', {})
                path = file.get('path', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_image(image=path, recipient_id=admin_config.phone_number, caption=caption, reply_to=replyMessageWamid))
                
            elif (message_type == self.MESSAGE_TYPE_VIDEO):
                file = components.get('file', {})
                path = file.get('path', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_video(video=path, recipient_id=admin_config.phone_number, caption=caption, reply_to=replyMessageWamid))
                
            elif (message_type == self.MESSAGE_TYPE_AUDIO):
                file = components.get('file', {})
                path = file.get('path', '')
                resp = asyncio.run(WhatsApps.send_audio(audio=path, recipient_id=admin_config.phone_number, reply_to=replyMessageWamid))

            elif (message_type == self.MESSAGE_TYPE_DOCUMENT):
                file = components.get('file', {})
                path = file.get('path', '')
                filename = file.get('name', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_document(document=path, recipient_id=admin_config.phone_number, caption=caption, link=True, filename=filename, reply_to=replyMessageWamid))
                
            elif (message_type == self.MESSAGE_TYPE_LOCATION):
                file = components.get('file', {})
                coordinates = file.get('coordinates', {})
                lat = coordinates.get('lat', '')
                lng = coordinates.get('lng', '') 
                addressname = file.get('name', '')
                address = file.get('address', '')
                resp = asyncio.run(WhatsApps.send_location(lat=lat, long=lng, name=addressname, address=address, recipient_id=admin_config.phone_number, reply_to=replyMessageWamid))

            elif (message_type == self.MESSAGE_TYPE_CONTACT):
                file = components.get('file', {})
                contacts = file.get('contact', {})
                resp = asyncio.run(WhatsApps.send_contacts(contacts=contacts, recipient_id=admin_config.phone_number, reply_to=replyMessageWamid))

            
                
            
            real_wamid = (resp.get("messages", [{}])[0].get("id"))
    
            if not real_wamid:
                return {
                    "error": True,           
                    "status_code": 502,      
                    "message": "WhatsApp API did not return a message ID",
                    "detail": resp.get('detail', {}).get('error', {})           
                    }
            
            admin_user_instance = getUserData.get('data')
            admin = getUserData['data'].owner_id
            
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            message = WhatsAppMessageQueryModel.save_message(
                validated_data = data,
                owner_id=admin_user_instance,
                admin=admin,
                wamid= real_wamid
                )
            return resp

        except Exception as e:
            app_logs("EXCEPTION", "Failed to sendmessage ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        

    def Schedulemessage(self, request, data):
        try:
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in getUserData and getUserData['error']):
                app_logs("ERROR", "User not found in DB ", {"error": getUserData, "inputData": request})
                return getUserData
            
            #user_id = request.data.get('to', '')

            admin_user_instance = getUserData.get('data')
            admin = getUserData['data'].owner_id
            message_type = data.get('type', '')
            WhatsAppMessageQueryModel = ScheduledMessageQuery()
            message = WhatsAppMessageQueryModel.insert_schedule_message(
                payload=data,
                admin_user=admin_user_instance,
                admin = admin,
                msg_type = message_type
                )
            return message

        except Exception as e:
            app_logs("ERROR", "Failed to schdeule message ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    

    def Sendscheduledmessage(self, payload, owner_id, sentto):
        try:
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(int(owner_id.owner_id))
            
            if ('error' in getUserData and getUserData['error']):
                app_logs("ERROR", "User Not Found in DB", {"error": getUserData, "inputData": owner_id.owner_id})
                return getUserData
            
            user_id = sentto

            admin_config = WhatsAppUser.objects.get(id=user_id)
            if not admin_config:
                app_logs("ERROR", "User Not Found in DB", {"error": admin_config, "inputData": user_id})
                return {'data' : ["User Not Found in DB"], 'error' : True}
            
            WhatsApps = WhatsApp(getUserData['data'].access_token, getUserData['data'].phone_number_id, getUserData['data'].waba_id, getUserData['data'].templates_access_token)  
            
            components = payload

            allowed_type = [self.MESSAGE_TYPE_TEXT, self.MESSAGE_TYPE_AUDIO, self.MESSAGE_TYPE_VIDEO, self.MESSAGE_TYPE_IMAGE, self.MESSAGE_TYPE_DOCUMENT, self.MESSAGE_TYPE_LOCATION]
            message_type = components.get('type', {})
            resp = None
            if (message_type and message_type not in allowed_type):
                response = {'data' : ['Not supported file type'], 'error' : True}
                return response
            
            if (message_type == self.MESSAGE_TYPE_TEXT):
                message = components.get('text', '')
                resp = asyncio.run(WhatsApps.send_message(message, admin_config.phone_number))
                
            elif (message_type == self.MESSAGE_TYPE_IMAGE):
                
                file = components.get('file', {})
                path = file.get('path', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_image(image=path, recipient_id=admin_config.phone_number, caption=caption))
                
            
            elif (message_type == self.MESSAGE_TYPE_VIDEO):
                
                file = components.get('file', '')
                path = file.get('path', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_video(video=path, recipient_id=admin_config.phone_number, caption=caption))
                
            
            elif (message_type == self.MESSAGE_TYPE_AUDIO):
                
                file = components.get('file', {})
                path = file.get('path', '')
                #caption = file.get('caption')
                resp = asyncio.run(WhatsApps.send_audio(audio=path, recipient_id=admin_config.phone_number))
                

            elif (message_type == self.MESSAGE_TYPE_DOCUMENT):
                
                file = components.get('file', {})
                path = file.get('path', '')
                filename = file.get('name', '')
                caption = file.get('caption', '')
                resp = asyncio.run(WhatsApps.send_document(document=path, recipient_id=admin_config.phone_number, caption=caption, link=True, filename=filename))
                
            
            elif (message_type == self.MESSAGE_TYPE_LOCATION):
                
                file = components.get('file', {})
                coordinates = file.get('coordinates', {})
                lat = coordinates.get('lat', '')
                lng = coordinates.get('lng', '') 
                addressname = file.get('name', '')
                address = file.get('address', '')

                resp = asyncio.run(WhatsApps.send_location(lat=lat, long=lng, name=addressname, address=address, recipient_id=admin_config.phone_number))

            
            real_wamid = (resp.get("messages", [{}])[0].get("id"))
            
            if not real_wamid:
                return {
                    "error": True,           
                    "status_code": 502,      
                    "message": "WhatsApp API did not return a message ID",
                    "detail": resp.get('detail', {}).get('errors', {})           
                    }
            
            admin_user_instance = getUserData.get('data')
            admin = getUserData['data'].owner_id
            
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            message = WhatsAppMessageQueryModel.save_message(
                validated_data = payload,
                owner_id=admin_user_instance,
                admin=admin,
                wamid= real_wamid
                )
            
            if "scheduled_at" in payload:
                payload.pop("scheduled_at", None)
            publish_to_stream(owner_id.owner_id, payload)
            return resp

        except Exception as e:
            app_logs("EXCEPTION", "Failed to Sendscheduledmessage ", {"error": str(traceback.format_exc()), "inputData": payload})
            return custom_exception_handler(e, {'view': self, 'request': payload})
        
    

    def Getconversations(self, request, conversation_id, offset, page_size):
        messageResponse = {'data': [], 'error' : True}
        try:
            admin_config = WhatsAppAdminUser.objects.get(owner=request.user)
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            res = WhatsAppMessageQueryModel.get_conversations_page_json(admin_config, conversation_id, offset, page_size)
           
            if ('error' in res and res['error']):
               logger.app_logs(
                    "ERROR",
                    "Failed to Getconversations data",
                    {"error": res['error'], "response": res}
                    )
               return messageResponse
            # datares = res['data']
            # res.pop('key', None)
            
            messageResponse = res

            return res

        except Exception as e:
            app_logs("ERROR", "Failed to Getconversations data ", {"error": str(traceback.format_exc()), "inputData": {request, conversation_id, offset, page_size}})  
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def markMessageAsRead(self, request, user_id):
        messageResponse = {'data': [], 'error' : True}
        try:
     
            
            admin_config = WhatsAppAdminUser.objects.get(owner=request.user)
    
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            res = WhatsAppMessageQueryModel.mark_messages_read(admin_config, user_id)
           
            if ('error' in res and res['error']):
               app_logs(
                    "ERROR",
                    "Failed to markMessageAsRead data",
                    {"error": res['error'], "response": res}
                    )
               return messageResponse
                                 
            
            messageResponse = {'data': res['data'], 'error' : False}

            return messageResponse

        except Exception as e:
            app_logs("EXCEPTION", "Failed to markMessageAsRead data ", {"error": str(traceback.format_exc()), "inputData": {request, user_id}})  
            return custom_exception_handler(e, {'view': self, 'request': request})
    
    def Sendreaction(self, request, data):
        try:
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in getUserData and getUserData['error']):
                return getUserData
            
            user_id = request.data.get('to', '')
            message_id = request.data.get('message_id', '')
            emoji = request.data.get('emoji', '')

            admin_config = WhatsAppUser.objects.get(id=user_id)
            if not admin_config:
                app_logs("ERROR", "User Not Found in DB", {"error": admin_config, "inputData": user_id})
                return {'data' : ["User Not Found in DB"], 'error' : True}
            
            
            WhatsApps = WhatsApp(getUserData['data'].access_token, getUserData['data'].phone_number_id, getUserData['data'].waba_id, getUserData['data'].templates_access_token)  
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            owner_id = str(getUserData['data'].id).replace('-', '')
            message_id_resp = WhatsAppMessageQueryModel.select_message(owner_id, message_id)
            if ('error' in message_id_resp and message_id_resp['error']):
               app_logs(
                    "ERROR",
                    "Failed to get message id",
                    {"error": message_id_resp['error'], "response": message_id_resp}
                    )
               return {'data' : ["Failed to get message id to send reaction"], 'error' : True}
            
            if ('data' in message_id_resp and message_id_resp['data'] and not message_id_resp['data']['id']):
                app_logs("ERROR", "", {"error": admin_config, "inputData": data})
                return {'data' : ["Message not found in DB to send reaction"], 'error' : True}

            resp = asyncio.run(WhatsApps.send_reaction(emoji, message_id, admin_config.phone_number))

            real_wamid = (resp.get("messages", [{}])[0].get("id"))
            
            if not real_wamid:
                return {
                    "error": True,           
                    "status_code": 502,      
                    "message": "WhatsApp API did not return a message ID",
                    "detail": resp.get('detail', {}).get('error', {})           
                    }
            
            WhatsAppMessageQueryModel = WhatsAppMessageQuery()
            message = WhatsAppMessageQueryModel.save_reaction(
                message_id=message_id_resp['data']['id'],
                user_id=user_id,
                emoji=emoji
                )
            return resp

        except Exception as e:
            app_logs("EXCEPTION", "Failed to Sendreaction ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


    def GetSchedulemessage(self, request, offset, page_size):
        try:
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in getUserData and getUserData['error']):
                return getUserData
            
            owner_id = str(getUserData['data'].id).replace('-', '')
            ScheduledMessageQueryModel = ScheduledMessageQuery()
            get_schedule_message_resp = ScheduledMessageQueryModel.get_schedule_message(owner_id, offset, page_size)
            if ('error' in get_schedule_message_resp and get_schedule_message_resp['error']):
               app_logs(
                    "ERROR",
                    "Failed to get get_schedule_message",
                    {"error": get_schedule_message_resp['error'], "response": get_schedule_message_resp}
                    )
               return {'data' : ["Failed to get get_schedule_message"], 'error' : True}
            
            if ('data' in get_schedule_message_resp):
                return get_schedule_message_resp['data']
            
            return response
        except Exception as e:
            app_logs("EXCEPTION", "Failed to get get_schedule_message", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
    
        

        

        
        
    
    