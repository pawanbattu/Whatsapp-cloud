import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from WhatsPanel.models.ScheduledMessage import *
from WhatsPanel.queries import *
from WhatsPanel.services.messageservice import *
from WhatsPanel.services.templateservice import *
from core.logger import app_logs
from core.utils import publish_to_stream
from core.file_utils import *
import datetime
from datetime import timezone as dt_timezone
from core.whatsapp_caller import WhatsApp
import asyncio
from minio.error import S3Error
from django.conf import settings
from minio import Minio
import mimetypes


@shared_task(bind=True, max_retries=1) 
def execute_whatsapp_dispatch(self, message_id):
    try:
        message = ScheduledMessage.objects.get(id=message_id, status='PENDING')
        
    except ScheduledMessage.DoesNotExist:
        app_logs("ERROR", "Failed to schdeule message does not exist in db", {"inputData": message_id})
        
        return False
    try:
        templateservicecls = templateservice()
        messageservicecls = messageservice()

        if (not message.template):
            app_logs("ERROR", "empty payload from db", {"inputData": message.template})
            message.status = 'FAILED'    
            message.save(update_fields=['status', 'updated_at'])
            return False
        
        if isinstance(message.template, str):
            try:
                payload = json.loads(message.template)
            except json.JSONDecodeError:
                payload = eval(message.template, {"datetime": datetime})
            else:
                payload = message.template

        if (not payload):
            app_logs("ERROR", "Failed to load payload into json", {"error": e, "inputData": message.template})
            message.status = 'FAILED'    
            message.save(update_fields=['status', 'updated_at'])
            return False

        if (not message.whatsapp_admin):
            app_logs("ERROR", "empty owner_id from db", {"inputData": message.whatsapp_admin})
            message.status = 'FAILED'    
            message.save(update_fields=['status', 'updated_at'])
            return False

        messageResponse = ''
        if (message.message_type == 'template'):
            
            messageResponse = templateservicecls.Sendscheduledtemplate(payload, message.whatsapp_admin, message.userid)    
        else:
            messageResponse = messageservicecls.Sendscheduledmessage(payload, message.whatsapp_admin, message.userid)
        
        if ("error" in messageResponse and messageResponse['error']):
            app_logs("ERROR", "Failed to send schdeule message from task ", {"error": messageResponse, "inputData": message})
            message.status = 'FAILED'    
            message.Error = messageResponse['error']
            message.save(update_fields=['status', 'Error', 'updated_at'])
        else:
            message.status = 'SENT'
            message.message_id = messageResponse.get('messages', [{}])[0].get('id')
            message.save(update_fields=['status', 'message_id', 'updated_at'])
        
    except requests.exceptions.RequestException as e:
        app_logs("WARNING", "Network error, retrying...", {"error": str(e)})    
        self.retry(exc=e, countdown=60) 
    except Exception as e:
        app_logs("EXCEPTION", "Fatal error, aborting", {"error": str(traceback.format_exc())})    
        message.status = 'FAILED'
        message.save(update_fields=['status'])

@shared_task
def poll_scheduled_messages():
    try:
        """
        Finds all pending messages where the scheduled time is now or in the past.
        """
        now = timezone.now()
        due_messages = ScheduledMessage.objects.filter(
            status='PENDING',
            scheduled_at__lte=now
        )
        
        for message in due_messages:
            execute_whatsapp_dispatch.delay(message.id)
    except Exception as e:
        app_logs("EXCEPTION", "poll_scheduled_messages", {"error": str(traceback.format_exc())})    

@shared_task
def process_whatsapp_webhook(data):
    """
    Processes the WhatsApp payload in the background.
    """
    #set dummy token and number
    messenger = WhatsApp("jiejrdjnfewjfwejfewfiwefwefnwfwifwfn", phone_number_id=63276426426282000000000000000000000)
    
    try:
        changed_field = messenger.changed_field(data)
        if changed_field == "messages":
            new_message = messenger.is_message(data)
            is_status = messenger.is_status(data)
            
            if new_message:
                mobile = messenger.get_mobile(data)
                message_type = messenger.get_message_type(data)
                message_id = messenger.get_message_id(data)
                name = messenger.get_name(data)
                waba_id = messenger.get_waba_id(data)
                reply_waba_id = messenger.get_message_reply_id(data)
                if reply_waba_id == message_id:
                    reply_waba_id = None

                if not waba_id:
                    app_logs("ERROR", "Failed to get waba_id", {"inputData": data})
                    return False
                
                if message_type in ['contact', 'contacts']:
                    message_type = 'contact'

                getUserDataBasedOnConditionRes = WhatsAppAdminUserQuery.getAdminUserDataBasedOnCondition({'waba_id': waba_id})

                if ('error' in getUserDataBasedOnConditionRes and getUserDataBasedOnConditionRes['error']):
                    app_logs("ERROR", "Error while getting getAdminUserDataBasedOnCondition", {"error": getUserDataBasedOnConditionRes['data'], "inputData": waba_id})
                    return getUserDataBasedOnConditionRes

                if ('data' in getUserDataBasedOnConditionRes and not getUserDataBasedOnConditionRes['data']):
                    app_logs("ERROR", "Empty data for the received message", {"error": getUserDataBasedOnConditionRes['data'], "inputData": data})
                    return getUserDataBasedOnConditionRes

                messenger = WhatsApp(
                    getUserDataBasedOnConditionRes['data'].access_token,
                    getUserDataBasedOnConditionRes['data'].phone_number_id,
                    getUserDataBasedOnConditionRes['data'].waba_id,
                    getUserDataBasedOnConditionRes['data'].templates_access_token
                )

                queryset = WhatsAppUser.objects.filter(phone_number=mobile, whatsapp_admin=getUserDataBasedOnConditionRes['data'])
                userData = queryset.first()

                if userData is None:
                    app_logs("INFO", f"User not present in DB Creating new one: {mobile} : {getUserDataBasedOnConditionRes['data']}")
                    new_user = WhatsAppUser.objects.create(
                        phone_number=mobile,
                        whatsapp_admin=getUserDataBasedOnConditionRes['data'],
                        whatsapp_name=name
                    )
                    if not new_user.pk:
                        app_logs("ERROR", "Failed to add new user", {"inputData": mobile})
                        return False
                    user_id = new_user.pk
                else:
                    user_id = userData.id

                admin_id = getUserDataBasedOnConditionRes['data'].owner_id

                payload = {
                    "id": message_id,
                    "userId": admin_id,
                    "sender_id": user_id,
                    "timestamp": timezone.now().isoformat(),
                    "type": message_type,
                    "text": None,
                    "file": None,
                    "reactions": {},
                    "forwarded": False,
                    "replyTo": None,           
                    "originalSenderId": None,
                    "originalTimestamp": None,
                    "reply_to_wamid" : reply_waba_id or None,
                    "wamid" : message_id,
                }

                try:
                    raw_message = data['entry'][0]['changes'][0]['value']['messages'][0]
                    context = raw_message.get('context', {})
                except (KeyError, IndexError, TypeError):
                    raw_message = {}
                    context = {}

                if context:
                    wamid = context.get('id', None)
                    if wamid is not None:
                        queryset = WhatsAppMessage.objects.filter(wamid=wamid, whatsapp_admin=getUserDataBasedOnConditionRes['data']).first()
                        if queryset:
                            payload["replyTo"] = queryset.id
                    payload["originalSenderId"] = context.get('from', 0)
                    payload["forwarded"] = context.get('forwarded', False)
                    payload["originalTimestamp"] = context.get('timestamp', None)


                if message_type == "text":
                    payload["text"] = messenger.get_message(data)

                elif message_type in ["image", "video", "audio", "document"]:
                    media = getattr(messenger, f"get_{message_type}")(data)
                    media_url = asyncio.run(messenger.query_media_url(media["id"]))

                    file_size_bytes = media.get("file_size", 0)
                    
                    if isinstance(file_size_bytes, (int, float)) and file_size_bytes > 0:
                        file_size_mb = max(round(file_size_bytes / (1024 * 1024), 2), 0.01)
                    else:
                        file_size_mb = 0

                    mime_type = media.get("mime_type", "")
                    
                    extension = mimetypes.guess_extension(mime_type) or f".{mime_type.split('/')[-1].split(';')[0]}"
                    extension = extension.lstrip('.')

                    filename = media.get("filename") or f"{media['id']}.{extension}"
                    path = process_whatsapp_media_task(media_url=media_url, mime_type=mime_type, whatsapp_client=messenger)

                    payload["file"] = {
                        "name": filename,
                        "size": file_size_mb,
                        "type": mime_type,
                        "preview": None,
                        "path": path,
                        "thumbnail": None,
                        "duration": media.get("duration", None),  
                        "caption": media.get("caption", ""),
                        "address": None,
                        "coordinates": None
                    }

                elif message_type == "location":
                    
                    try:
                        raw_location = data['entry'][0]['changes'][0]['value']['messages'][0].get('location', {})
                    except (KeyError, IndexError, TypeError):
                        raw_location = {}

                    lat = raw_location.get('latitude')
                    lng = raw_location.get('longitude')
                    name = raw_location.get('name') or None
                    address = raw_location.get('address') or None
                    coordinates_str = json.dumps({"lat": lat, "lng": lng}) if lat is not None and lng is not None else None

                    payload["file"] = {
                        "name": name,
                        "size": None,
                        "type": None,
                        "preview": None,
                        "path": None,
                        "thumbnail": None,
                        "duration": None,
                        "caption": None,
                        "address": address,
                        "coordinates": coordinates_str
                    }

                elif message_type == "reaction":
                    try:
                        reaction_data = data['entry'][0]['changes'][0]['value']['messages'][0].get('reaction', {})
                    except (KeyError, IndexError, TypeError):
                        reaction_data = {}

                    payload["reactions"] = {reaction_data.get('emoji', '') : [6]}
                    payload["reply_to_wamid"] = reaction_data.get('message_id', '')
                    #"message_id": reaction_data.get('message_id', '')
                        
                elif message_type == "sticker":
                    sticker = messenger.get_sticker(data) if hasattr(messenger, 'get_sticker') else {}
                    if sticker:
                        media_url = asyncio.run(messenger.query_media_url(sticker["id"]))
                        payload["file"] = {
                            "name": f"{sticker['id']}.webp",
                            "size": sticker.get("file_size", 0),
                            "type": sticker.get("mime_type", "image/webp"),
                            "preview": None,
                            "path": media_url,
                            "thumbnail": None,
                            "duration": None,
                            "caption": None,
                            "address": None,
                            "coordinates": None
                        }
                
                elif message_type in ["contact", "contacts"]:  
                    try:
                        raw_contacts = data['entry'][0]['changes'][0]['value']['messages'][0].get('contacts', [])
                    except (KeyError, IndexError, TypeError):
                        raw_contacts = []

                    if raw_contacts:
                        contact_data = raw_contacts[0]
                        formatted_name = contact_data.get("name", {}).get("formatted_name", "Unknown Contact")    
                        payload["file"] = {
                            "name": formatted_name,
                            "size": 0,     
                            "type": "contact",     
                            'path': "contact",
                            "preview": None,
                            "contact": contact_data,
                            "caption": ""
                        }

                elif message_type == "interactive":
                    try:
                        interactive_data = data['entry'][0]['changes'][0]['value']['messages'][0].get('interactive', {})
                    except (KeyError, IndexError, TypeError):
                        interactive_data = {}

                    interactive_type = interactive_data.get('type')  
                    if interactive_type == 'button_reply':
                        reply = interactive_data.get('button_reply', {})
                        payload["text"] = reply.get('title', '')
                    elif interactive_type == 'list_reply':
                        reply = interactive_data.get('list_reply', {})
                        payload["text"] = reply.get('title', '')
                    else:
                        payload["text"] = json.dumps(interactive_data)

                elif message_type == "button":
                    try:
                        button_data = data['entry'][0]['changes'][0]['value']['messages'][0].get('button', {})
                    except (KeyError, IndexError, TypeError):
                        button_data = {}
                    payload["text"] = button_data.get('text', '')

                else:
                    app_logs("WARNING", f"Unhandled message type: {message_type}", {"inputData": data})

                WhatsAppMessageQuerycls = WhatsAppMessageQuery()
                owner_id = str(getUserDataBasedOnConditionRes['data'].id).replace('-', '')
                insertMessage = WhatsAppMessageQuerycls.insert_whatsapp_message(payload, owner_id)
                app_logs("INFO", f"New Message Insert : {insertMessage}")
                publish_to_stream(admin_id, payload)
            elif is_status:
                status_obj = messenger.get_status(data)
                mobile = status_obj.get("recipient_id")
                status_type = status_obj.get("status") 
                message_id = status_obj.get("id")   
                waba_id = data["entry"][0].get("id") 

                getUserDataBasedOnConditionRes = WhatsAppAdminUserQuery.getAdminUserDataBasedOnCondition({'waba_id': waba_id})
                if ('error' in getUserDataBasedOnConditionRes and getUserDataBasedOnConditionRes['error']):
                    app_logs("ERROR", "Error while getting getAdminUserDataBasedOnCondition", {"error": getUserDataBasedOnConditionRes['data'], "inputData": waba_id})
                    return getUserDataBasedOnConditionRes

                if ('data' in getUserDataBasedOnConditionRes and not getUserDataBasedOnConditionRes['data']):
                    app_logs("ERROR", "Empty data for the received status message", {"error": getUserDataBasedOnConditionRes['data'], "inputData": data})
                    return getUserDataBasedOnConditionRes
                
                WhatsAppMessageQueryModel = WhatsAppMessageQuery()
                owner_id = str(getUserDataBasedOnConditionRes['data'].id).replace('-', '')
                
                message_id_resp = WhatsAppMessageQueryModel.select_message(owner_id, message_id)
                if ('error' in message_id_resp and message_id_resp['error']):
                    app_logs("ERROR", "Failed to get message id", {"error": message_id_resp['error'], "response": message_id_resp})
                    return {'data': ["Failed to get message id"], 'error': True}
                
                if ('data' in message_id_resp and message_id_resp['data'] and not message_id_resp['data'].get('id')):
                    app_logs("ERROR", "Message not found in DB to update status", {"error": message_id_resp, "inputData": data})
                    return {'data': ["Message not found in DB to update status"], 'error': True}
                
                status_text = None

                if status_type == "failed" and "errors" in status_obj:
                    error_code = status_obj["errors"][0].get("code")
                    error_title = status_obj["errors"][0].get("title")
                    error_data = status_obj["errors"][0].get("error_data")
                    error_message = status_obj["errors"][0].get("message")
                    
                    app_logs(
                        "ERROR", 
                        f"Message Delivery Failed (Code: {error_code}) - {error_title}", 
                        {"status_obj": status_obj}
                    )
                    
                    error_payload = {
                        "code": error_code,
                        "title": error_title,
                        "status_type": status_type,
                        "error_data" : error_data,
                        "error_message" : error_message,
                    }
                    status_text = json.dumps(error_payload)
                
                elif status_type in ["sent", "delivered", "read"]:
                    if status_type == "read":
                        timestamp = status_obj.get("timestamp")
                        timestamp_int = int(timestamp)
                        read_at_datetime = datetime.datetime.fromtimestamp(timestamp_int, tz=dt_timezone.utc)
                        WhatsAppMessageQueryModel.mark_messages_read(getUserDataBasedOnConditionRes['data'], None, read_at_datetime, message_id)
                
                WhatsAppMessageQueryModel.update_message(status_type, status_text, owner_id, message_id)                        
                    
    except Exception as e:
        app_logs("EXCEPTION", "Failed to get process recieving message ", {"error": str(traceback.format_exc()), "inputData": data})
        raise



# @shared_task(bind=True, max_retries=2)
def process_whatsapp_media_task(media_url: str, mime_type: str, whatsapp_client: object):
    
    file_base_path = f"temp_{uuid.uuid4()}"
    downloaded_file_path = None
    
    try:    
        download_file_path = get_upload_temp_dir(file_base_path)
        downloaded_file_path = asyncio.run(
            whatsapp_client.download_media(media_url, mime_type, file_path=download_file_path)
        )

        if not downloaded_file_path:
            app_logs("ERROR", "Failed to download media ", {"error": downloaded_file_path, "inputData": media_url})
            raise ValueError("download_media returned None.")
        
        file_size = os.path.getsize(downloaded_file_path)
        file_name = os.path.basename(downloaded_file_path)
        object_name = f"uploads/{uuid.uuid4()}_{file_name}"

        MINIO_BUCKET = getattr(settings, 'MINIO_BUCKET', 'whatsappmedia')
        MINIO_ENDPOINT = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000') 
        MINIO_URL = getattr(settings, 'MINIO_URL', 'http://localhost') 
        
        minio_client = Minio(
            endpoint= getattr(settings, 'MINIO_ENDPOINT', MINIO_ENDPOINT),
            access_key=getattr(settings, 'MINIO_ACCESS_KEY', 'minio'),
            secret_key=getattr(settings, 'MINIO_SECRET_KEY', 'minio123'),
            secure=getattr(settings, 'MINIO_SECURE', False),      
        )

        with open(downloaded_file_path, "rb") as file_data:
            if not minio_client.bucket_exists(MINIO_BUCKET):
                minio_client.make_bucket(MINIO_BUCKET)
            minio_client.put_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=mime_type or 'application/octet-stream',
            )

        minio_url = f"{MINIO_URL}/{MINIO_BUCKET}/{object_name}"
        
        return minio_url

    except Exception as exc:
        app_logs("ERROR", "Failed to process_whatsapp_media_task ", {"error": str(traceback.format_exc()), "inputData": media_url})
        
        # 2. Explicitly tell Celery to retry this task. 
        # countdown=60 means it will wait 60 seconds before trying again.
        #raise self.retry(exc=exc, countdown=60) 
        
    finally:        
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)