import core.logger as logger
import traceback
from WhatsPanel.models import *
from django.db.models.query import RawQuerySet

class WhatsAppAdminUserQuery():
    def __init__(self):
        pass
    
    @staticmethod
    def getUserData(userid):
        response = {"data" : [], 'error' : True}
        try:
        
            obj = WhatsAppAdminUser.objects.filter(owner=userid).first()
            
            if not obj or not (obj.access_token and obj.templates_access_token and obj.phone_number_id and obj.waba_id and obj.app_id):
                logger.app_logs("ERROR", "Please Save All the details in setting", {"response": obj, "inputData": userid })    
                response['data'] = 'Please Save All the details in setting'
                return response
            else:
                return {'error': False, 'data': obj}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to getUserData", {"error": str(traceback.format_exc()), "response": response})    

            return response
        
    @staticmethod
    def saveUserData(userid, access_token):
        response = {"data" : [], 'error' : True}
        try:
            updated_count = WhatsAppAdminUser.objects.filter(owner=userid).update(access_token=access_token)

            if updated_count > 0:
                return {'error': False, 'data': updated_count}
            else:
                return {'error': True, 'data': updated_count}
            
        except Exception as e:
            logger.app_logs("ERROR", "Failed to saveUserData", {"error": str(traceback.format_exc()), "response": response})    

            return response
        
    @staticmethod
    def getAdminUserDataBasedOnCondition(data):
        response = {"data" : [], 'error' : True}
        try:
            if ("waba_id" in data):
                obj = WhatsAppAdminUser.objects.filter(waba_id=data['waba_id']).first()
            elif('owner' in data):
                obj = WhatsAppAdminUser.objects.filter(owner=data['owner']).first()
            
            if not obj or not (obj.access_token and obj.templates_access_token and obj.phone_number_id and obj.waba_id and obj.app_id):
                logger.app_logs("ERROR", "Please Save All the details in setting", {"response": obj, "inputData": data })    
                response['data'] = 'Please Save All the details in setting'
                return response
            else:
                return {'error': False, 'data': obj}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to getAdminUserDataBasedOnCondition", {"error": str(traceback.format_exc()), "response": response})    

            return response
        
