from rest_framework.response import Response
from WhatsPanel.models import *
from core.logger import app_logs
import traceback
import json
from django.db import connections
from core.responses import response
from WhatsPanel.queries import *
from core.whatsapp_caller import WhatsApp
import asyncio
import os
from core.utils import success_response, custom_exception_handler



class templateservice():
    def __init__(self):
        pass

    def Sendtemplate(self, request):
        try:
            response = {'data' : [], 'error' : True}
            
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            
            
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  
            
            components = request.data
                        
            
            admin_config = WhatsAppUser.objects.filter(id=components['to']).first()
            if not admin_config:
                app_logs("ERROR", "User Not Found in DB", {"error": admin_config, "inputData": components['to']})
                return {'data' : ["User Not Found in DB"], 'error' : True}
            
            recipient_id = admin_config.phone_number
            
            components_to_pass = components['components']

            templateName = components['templateName']

            # Get original template components array
            WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
            originaltemplate = WhatsAppTemplateQueryModel.getTemplate(templateName, request.user)
            if ('error' in originaltemplate and originaltemplate['error']):
                app_logs("ERROR", "Failed to fetch whatsapp template ", {"error": originaltemplate, "inputData": templateName})  
                return {'data' : ['Error While fetching template'], 'error' : True}
            
            if ('data' in originaltemplate and not originaltemplate['data']):
                app_logs("ERROR", "Template does not exists in db if you imported already existed template then sync them from templates menu", {"error": originaltemplate, "inputData": templateName})  
                return {'data' : ['Template does not exists in db if you imported already existed template then sync them from templates menu'], 'error' : True}

            originaltemplatedata = originaltemplate['data']

            originalTemplateComponents = originaltemplatedata.components or [] 
        
            
            original_body_text = None
            for comp in originalTemplateComponents:
                
                if comp.get("type") == "BODY":
                    original_body_text = comp.get("text", "")
                    break
            
            component = WhatsApps.build_whatsapp_components(components_to_pass, original_template_body=original_body_text)
            
            resp = asyncio.run(WhatsApps.send_template(template=templateName, recipient_id=recipient_id, components=component,lang="en_US"))

            if ('error' in resp):
                return {'data' : [resp['error']], 'error' : True}

            status = None
            if isinstance(resp.get("messages"), list) and resp["messages"]:
                status = resp["messages"][0].get("message_status")
                if status == 'accepted':    
                    real_wamid = (resp.get("messages", [{}])[0].get("id"))
                    admin_user_instance = data.get('data')
                    admin = data['data'].owner_id
                    WhatsAppMessageQueryModel = WhatsAppMessageQuery()
                    save_conversation = WhatsAppMessageQueryModel.save_conversation(components, 'template', admin_user_instance, admin, real_wamid)
                    
                    return {'data' : [], 'error' : False}
                
            app_logs("ERROR", "Failed to sendtemplate ", {"error": resp, "inputData": request})  
            return {'data' : ['Error While sending template'], 'error' : True}

        except Exception as e:
            app_logs("ERROR", "Failed to sendtemplate ", {"error": str(traceback.format_exc()), "inputData": request})  
            raise
            

        
    

    def Savetemplate(self, request):
        try:
            
            templateResponse = {'data' : [], 'error': True} 
            WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
            data = request.data.get('template_data')
            #for i in data:
            saveTemplate = WhatsAppTemplateQueryModel.saveTemplate(data, request.user)

            if ('error' in saveTemplate and saveTemplate['error']):
                logger.app_logs("ERROR", "Failed to save template data", {"error": saveTemplate['error'], "response": saveTemplate})       

                return templateResponse
            return {'data' : [], 'error': False} 
        except Exception as e:
            app_logs("ERROR", "Failed to save template data", {"error": str(traceback.format_exc()), "inputData": request.data})  
            raise

        return templateResponse
    
    def getTemplate(self, request, from_db = 1, all_data = ''):
        try:
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            
            if (from_db == 1):
                WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
                list_template = WhatsAppTemplateQueryModel.getTemplate(user_id=request.user, json=1, all_data=all_data)
            else:
                WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

                list_template = asyncio.run(WhatsApps.list_template())

                if ('error' in list_template and list_template['error']):
                    logger.app_logs("ERROR", "Failed to save template data", {"error": list_template['error'], "response": list_template})       
                    
                    return list_template
            
            return {'data' : list_template['data'], 'error': list_template['error']} 
        
        except Exception as e:
            app_logs("ERROR", "Failed to get template data", {"error": str(traceback.format_exc()), "inputData": request.data})  
            raise
            #return custom_exception_handler(e, {'view': self, 'request': request})
        
    def Synctemplate(self, request):
        try:
            templateResponse = {'data' : [], 'error': True} 
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            list_template = asyncio.run(WhatsApps.list_template())

            if ('error' in list_template and list_template['error']):
                logger.app_logs("ERROR", "Failed to sync template data", {"error": list_template['error'], "response": list_template})       
                
                return list_template
            
            templates = list_template.get("data", {}).get("data", [])
            if isinstance(templates, list):
                WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
                for template in templates:
                    updateTemplate = WhatsAppTemplateQueryModel.updateTemplate(template, request.user)

                    if ('error' in updateTemplate and updateTemplate['error']):
                        logger.app_logs("ERROR", "Failed to save template data", {"error": updateTemplate['error'], "response": updateTemplate})       

                        return templateResponse

            return {'data' : "Template sync done", 'error': list_template['error']} 
        
        except Exception as e:
            app_logs("ERROR", "Failed to sync template data", {"error": str(traceback.format_exc()), "inputData": request.data})  
            raise
            #return custom_exception_handler(e, {'view': self, 'request': request})
    
        
    

    def submitTemplate(self, request):
        try:  
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            
            template_data = request.data.get('template_data')

            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            save_template = asyncio.run(WhatsApps.submit_template(template_data))

            if ('error' in save_template and save_template['error']):
                logger.app_logs("ERROR", "Failed to save template data", {"error": save_template['error'], "response": save_template})       

                return save_template
            
            save_template = self.Savetemplate(request)

            return {'data' : save_template['data'], 'error': False} 
        except Exception as e:
            app_logs("ERROR", "Failed to save template data", {"error": str(traceback.format_exc()), "inputData": request})  
            raise
            #return custom_exception_handler(e, {'view': self, 'request': request})
        
    
    def deleteTemplate(self, request, template_name=None):
        try:  
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            

            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            delete_template = asyncio.run(WhatsApps.delete_template(template_name))

            if ('error' in delete_template and delete_template['error']):
                logger.app_logs("ERROR", "Failed to delete template data", {"error": delete_template['error'], "response": delete_template, "inputData": template_name})       

                return delete_template
            WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
            deleteTemplate = WhatsAppTemplateQueryModel.deleteTemplate(template_name, request.user)

            if ('error' in deleteTemplate and deleteTemplate['error']):
                logger.app_logs("ERROR", "Failed to delete template data from db", {"error": deleteTemplate['error'], "response": deleteTemplate, "inputData" : template_name})       

                return deleteTemplate
            
            return {'data' : delete_template['data'], 'error': False} 
        except Exception as e:
            app_logs("ERROR", "Failed to delete template data", {"error": str(traceback.format_exc()), "inputData": {request}})  
            raise
            #return custom_exception_handler(e, {'view': self, 'request': request})    
        
    def editTemplate(self, request, template_id=None):
        try:  
            data = WhatsAppAdminUserQuery.getUserData(request.user)
            if ('error' in data and data['error']):
                return data
            
            template_data = request.data.get('template_data')

            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  

            edit_template = asyncio.run(WhatsApps.edit_template(template_data, template_id))

            if ('error' in edit_template and edit_template['error']):
                logger.app_logs("ERROR", "Failed to edit template data", {"error": edit_template['error'], "response": edit_template, "inpuData" : {"template_id": template_id, "template_data": template_data}})       

                return edit_template
            
            WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
            editTemplate = WhatsAppTemplateQueryModel.updateTemplate(template_data, request.user)

            if ('error' in editTemplate and editTemplate['error']):
                logger.app_logs("ERROR", "Failed to delete template data from db", {"error": editTemplate['error'], "response": editTemplate, "inputData" : template_data})       

                return editTemplate

            return {'data' : edit_template['data'], 'error': False} 
        except Exception as e:
            app_logs("ERROR", "Failed to edit template data", {"error": str(traceback.format_exc()), "inputData": request})  
            raise
            #return custom_exception_handler(e, {'view': self, 'request': request})

    def scheduleTemplate(self, request, data):
        try:  
            response = {'data' : [], 'error' : True}
            
            getUserData = WhatsAppAdminUserQuery.getUserData(request.user)
            
            if ('error' in getUserData and getUserData['error']):
                app_logs("ERROR", "User not found in DB ", {"error": getUserData, "inputData": request})
                return getUserData
            
            #user_id = request.data.get('to', '')
            app_logs("ERROR", "User not found in DB ", {"error": data, "inputData": request})

            admin_user_instance = getUserData.get('data')
            admin = getUserData['data'].owner_id
            
            WhatsAppMessageQueryModel = ScheduledMessageQuery()
            message = WhatsAppMessageQueryModel.insert_schedule_message(
                payload=data,
                admin_user=admin_user_instance,
                admin = admin,
                msg_type = 'template'
                )
            return message

        except Exception as e:
            app_logs("ERROR", "Failed to schdeule templare ", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        
    def Sendscheduledtemplate(self, payload, owner_id, sentto):
        try:
            response = {'data' : [], 'error' : True}
            
            data = WhatsAppAdminUserQuery.getUserData(int(owner_id.owner_id))
            if ('error' in data and data['error']):
                app_logs("ERROR", "User Not Found in DB", {"error": data, "inputData": owner_id.owner_id})
                return data            
            
            WhatsApps = WhatsApp(data['data'].access_token, data['data'].phone_number_id, data['data'].waba_id, data['data'].templates_access_token)  
            
            components = payload
                        
            
            admin_config = WhatsAppUser.objects.filter(id=sentto).first()
            if not admin_config:
                app_logs("ERROR", "User Not Found in DB", {"error": admin_config, "inputData": sentto})
                return {'data' : ["User Not Found in DB"], 'error' : True}
            
            recipient_id = admin_config.phone_number
            
            components_to_pass = components['components']

            templateName = components['templateName']

            # Get original template components array
            WhatsAppTemplateQueryModel = WhatsAppTemplateQuery()
            originaltemplate = WhatsAppTemplateQueryModel.getTemplate(templateName, owner_id.owner_id)
            originaltemplatedata = originaltemplate['data']
            originalTemplateComponents = originaltemplatedata.components or [] 

            original_body_text = None
            for comp in originalTemplateComponents:
                
                if comp.get("type") == "BODY":
                    original_body_text = comp.get("text", "")
                    break
            
            component = WhatsApps.build_whatsapp_components(components_to_pass, original_template_body=original_body_text)
            
            resp = asyncio.run(WhatsApps.send_template(template=templateName, recipient_id=recipient_id, components=component,lang="en_US"))

            if ('error' in resp):
                return {'data' : [resp['error']], 'error' : True}

            status = None
            if isinstance(resp.get("messages"), list) and resp["messages"]:
                status = resp["messages"][0].get("message_status")
            
            if status == 'accepted':
                
                admin_user_instance = data.get('data')
                admin = data['data'].owner_id
                WhatsAppMessageQueryModel = WhatsAppMessageQuery()
                save_conversation = WhatsAppMessageQueryModel.save_conversation(components, 'template', admin_user_instance, admin)

                if "scheduled_at" in payload:
                    payload.pop("scheduled_at", None)
                    
                publish_to_stream(owner_id.owner_id, components)
                return {'data' : [], 'error' : False}

        except Exception as e:
            app_logs("ERROR", "Failed to Sendscheduledtemplate ", {"error": str(traceback.format_exc()), "inputData": {payload, owner_id}})  
            raise