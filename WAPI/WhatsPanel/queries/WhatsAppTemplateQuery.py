import core.logger as logger
import traceback
from WhatsPanel.models import *
from django.db import connection
from django.db.models.query import RawQuerySet
import json as py_json

class WhatsAppTemplateQuery():
    def __init__(self):
        pass
    
    def saveTemplate(self, data, user_id):
        response = {"data" : [], 'error' : True}
        try:
           admin_config = WhatsAppAdminUser.objects.get(owner=user_id)
           res = WhatsAppTemplate.objects.create(
               template_id = data.get('id'),
               name = data.get('name'),
               language = data.get('language'),
               category = data.get('category'),
               status = data.get('status'),
               components = data.get('components'),
               parameter_format = data.get('parameter_format'),
               whatsapp_admin = admin_config
               )
           if res.pk:
            response = {"data" : res.pk, 'error' : False}
              
            return response
        except Exception as e:
            logger.app_logs("ERROR", "Failed to save template Data ", {"error": str(traceback.format_exc()), "response": response, 'inputData' : data})    

            return response
        
    def getTemplate(self, templateName = '', user_id = 0, json = 0, all_data = ''):
        response = {"data" : [], 'error' : True}
        try:
            admin_config = WhatsAppAdminUser.objects.get(owner=user_id)
            if (json == 1):
                query = """
                SELECT JSON_OBJECT(
                    'data', JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'name', name,
                            'parameter_format', parameter_format,
                            'components', components,
                            'language', language,
                            'status', status,
                            'category', category,
                            'id', template_id
                        )
                    )
                ) AS response
                FROM WhatsPanel_whatsapptemplate
                WHERE user_id = %s;
                """
                params = [admin_config.id.hex]
                if all_data != '':
                    query += """AND status = %s"""
                    params.append(str(all_data))
                
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        response_data = py_json.loads(row[0]) 
                        
                        if response_data.get('data') is None:
                            response_data['data'] = []
                            
                        response = {"data": response_data['data'], "error": False}
                    else:
                        response = {"data": [], "error": False}
            else: 
                res = WhatsAppTemplate.objects.get(name = templateName, whatsapp_admin = admin_config)
                if res:
                    response = {"data" : res, 'error' : False}
              
            return response
        
        except WhatsAppTemplate.DoesNotExist:
            logger.app_logs("EXCEPTION", "Template does not exists in db if you imported already existed template then sync them from templates menu", {"error": str(traceback.format_exc()), "response": response, 'inputData' : templateName})    
            return {"data": [], "error": False}
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to getTemplate Data ", {"error": str(traceback.format_exc()), "response": response, 'inputData' : templateName})    

            return response
        
    def deleteTemplate(self, templateName, user_id):
        response = {"data" : [], 'error' : True}
        try:
           admin_config = WhatsAppAdminUser.objects.get(owner=user_id)
           res = WhatsAppTemplate.objects.filter(name = templateName, whatsapp_admin = admin_config).delete()
           if res:
            response = {"data" : res, 'error' : False}
              
            return response
        except Exception as e:
            logger.app_logs("ERROR", "Failed to deleteTemplate Data ", {"error": str(traceback.format_exc()), "response": response, 'inputData' : templateName})    

            return response
        
    def updateTemplate(self, data, user_id):
        response = {"data": [], "error": True}
        try:
            admin_config = WhatsAppAdminUser.objects.get(owner=user_id)

            obj, created = WhatsAppTemplate.objects.update_or_create(
                whatsapp_admin=admin_config,
                name=data.get('name'),  # lookup field
                defaults={
                    "template_id": data.get('id'),
                    "language": data.get('language'),
                    "category": data.get('category'),
                    "status": data.get('status', 'PENDING'),
                    "components": data.get('components'),
                    "parameter_format": data.get('parameter_format'),
                }
            )

            response = {
                "data": data,
                "error": False,
                "message": "Template created" if created else "Template updated"
            }
            return response

        except Exception as e:
            logger.app_logs(
                "ERROR",
                "Failed to upsert template Data",
                {
                    "error": str(traceback.format_exc()),
                    "inputData": data,
                }
            )
            return response
            
    