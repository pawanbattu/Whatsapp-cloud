import core.logger as logger
import traceback
from WhatsPanel.models import *
from django.db.models.query import RawQuerySet

class WhatsAppUserQuery():
    def __init__(self):
        pass
    
    def getUser(self, getallusers = 1, owner_id = ''):
        
        response = {"data" : [], 'error' : True}
        try:
            params = [owner_id]

            if (getallusers == 1):
                query = """
                SELECT * from WhatsPanel_whatsappuser
                where owner_id = %s
                """
            else:
                query = """
               SELECT 
                usr.id,
                usr.whatsapp_name as name, 
                usr.last_user_message_at as lastSeen,
                usr.avatar,
                MAX(msg.wa_timestamp) as last_message_time
            FROM WhatsPanel_whatsappuser AS usr
            LEFT JOIN whatsapp_messages AS msg ON usr.id = msg.userid
            WHERE usr.owner_id = %s
            GROUP BY 
                usr.id,
                usr.whatsapp_name,
                usr.last_user_message_at,
                usr.avatar
            ORDER BY last_message_time DESC;
                """
            
            users = WhatsAppUser.objects.raw(query, params)
            
            if isinstance(users, RawQuerySet):
                users_list = list(users)
                if users_list:
                    
                    response = {"data" : users_list, 'error' : False}

            return response
        except Exception as e:
            logger.app_logs("ERROR", "Failed to getUser Data ", {"error": str(traceback.format_exc()), "response": response})    

            return response
        
    def getUserBasedOnCondition(self, phone_number, owner_id):
        
        response = {"data" : [], 'error' : True}
        try:
            params = [phone_number, owner_id]

            
            query = """
                SELECT * from WhatsPanel_whatsappuser
                where owner_id = %s
                ORDER BY last_user_message_at DESC, 
                created_at DESC limit 1
                """
            
            users = WhatsAppUser.objects.raw(query, params)
            
            if isinstance(users, RawQuerySet):
                users_list = list(users)
                if users_list:
                    response = {"data" : users_list, 'error' : False}

            return response
        except Exception as e:
            logger.app_logs("ERROR", "Failed to getUser Data ", {"error": str(traceback.format_exc()), "response": response})    

            return response
        