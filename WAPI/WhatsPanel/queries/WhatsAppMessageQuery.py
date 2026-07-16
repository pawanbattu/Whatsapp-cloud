import core.logger as logger
import traceback
from WhatsPanel.models import *
from django.db.models.query import RawQuerySet
import json
import time
from datetime import datetime
from django.db import transaction
from django.utils import timezone
import uuid
from core.utils import *
from django.db import connection

class WhatsAppMessageQuery():
    def __init__(self):
        pass

    def get_conversations_json_(self, data):
        response = {"data" : [], 'error' : True}
        try:
            sql = """
SELECT 
    1 as id, 
    JSON_OBJECTAGG(conversation_id, messages) as json_data
FROM (
    SELECT 
        m.userid AS conversation_id,
        JSON_ARRAYAGG(
            JSON_OBJECT(
                'id', CAST(m.id AS CHAR),
                'text', m.text_content,
                'userId', m.sender_userid,
                'timestamp', DATE_FORMAT(m.created_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ'),
                'type', m.message_type,
                'forwarded', IF(m.forwarded = 1, TRUE, FALSE),
                'originalSenderId', m.originalSenderId,
                'originalTimestamp', DATE_FORMAT(m.originalTimestamp, '%%Y-%%m-%%dT%%H:%%i:%%sZ'),
                'replyTo', CAST(m.reply_to_wamid AS CHAR),
                'file', IF(
                    f.id IS NOT NULL OR m.address IS NOT NULL OR m.coordinates IS NOT NULL,
                    JSON_OBJECT(
                        'name', f.name, 
                        'size', f.size, 
                        'type', f.type,
                        'preview', f.preview, 
                        'path', f.path,
                        'thumbnail', f.thumbnail, 
                        'duration', f.duration, 
                        'caption', f.caption,
                        'address', m.address,
                        'coordinates', m.coordinates
                    ),
                    NULL
                ),
                'reactions', COALESCE(r.reactions_json, JSON_OBJECT()),
                'template', m.template
            )
            
        ) AS messages
    FROM whatsapp_messages m
    LEFT JOIN whatsapp_media f ON m.media_id = f.id
    LEFT JOIN (
        SELECT 
            message, 
            JSON_OBJECTAGG(emoji, user_list) AS reactions_json
        FROM (
            SELECT message, emoji, JSON_ARRAYAGG(user) as user_list
            FROM WhatsPanel_whatsappreaction
            GROUP BY message, emoji
        ) reaction_grouped
        GROUP BY message
    ) r ON m.id = r.message
    where m.owner_id = %s
    GROUP BY m.userid
    ORDER BY m.id
) conversation_groups;
"""


            res = WhatsAppMessage.objects.raw(sql, [data.id.hex])
            #print(res)
            if isinstance(res, RawQuerySet):
                data = res[0].json_data
                
                if isinstance(data, str):
                    data = json.loads(data)
                    response = {"data" : data, 'error' : False}
        except IndexError:
                data = {"conversations": {}}            
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get messages ", {"error": str(traceback.format_exc()), "response": response})    

        return response
    
    def get_conversations_json(self, data):
        response = {"data" : [], 'error' : True}
        try:
            sql = """
                WITH RankedMessages AS (
                    SELECT 
                        m.userid AS conversation_id,
                        m.id,
                        m.wamid,
                        m.text_content,
                        m.sender_userid,
                        m.created_at,
                        m.message_type,
                        m.forwarded,
                        m.originalSenderId,
                        m.originalTimestamp,
                        m.reply_to_wamid,
                        m.address,
                        m.coordinates,
                        m.is_read,
                        m.read_at,
                        m.template,
                        m.wa_timestamp,
                        m.status,
                        m.error_text,
                        f.name  AS file_name,
                        f.size  AS file_size,
                        f.type  AS file_type,
                        f.preview AS file_preview,
                        f.caption AS file_caption,
                        f.path AS file_path,
                        f.contact_phones AS contact_phones,
                        f.contact_emails AS contact_emails,
                        f.contact_org AS contact_org,
                        f.contact_name AS contact_name,
                        r.reactions_json,
                        
                        ROW_NUMBER() OVER (
                            PARTITION BY m.userid 
                            ORDER BY m.wa_timestamp DESC, m.id DESC
                        ) AS message_rank
                    FROM whatsapp_messages m
                    LEFT JOIN whatsapp_media f ON m.media_id = f.id
                    LEFT JOIN (
                        SELECT 
                            message,
                            JSON_OBJECTAGG(emoji, user_list) AS reactions_json
                        FROM (
                            SELECT message, emoji, JSON_ARRAYAGG(user) AS user_list
                            FROM WhatsPanel_whatsappreaction
                            GROUP BY message, emoji
                        ) rg
                        GROUP BY message
                    ) r ON m.id = r.message
                    WHERE m.owner_id = %s
                )
                SELECT 
                    conversation_id,
                    id,
                    wamid,
                    text_content,
                    sender_userid,
                    created_at,
                    message_type,
                    forwarded,
                    wa_timestamp,
                    originalSenderId,
                    originalTimestamp,
                    reply_to_wamid,
                    address,
                    coordinates,
                    template,
                    is_read,
                    read_at,
                    status,
                    error_text,
                    file_name,
                    file_size,
                    file_type,
                    file_preview,
                    file_caption,
                    file_path,
                    contact_phones,
                    contact_emails,
                    contact_org,
                    contact_name,
                    reactions_json
                FROM RankedMessages
                WHERE message_rank <= 50

                ORDER BY conversation_id ASC, wa_timestamp ASC;
            """
            rows = None
            with connection.cursor() as cursor:
                cursor.execute(sql, [data.id.hex])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                if not rows:
                    return {"data" : [], 'error' : False}
            conversations = {}
            count_message_res = self.count_message(data.id.hex)
            message_count = {}
            if ('error' in count_message_res and not count_message_res['error']):
                message_count = count_message_res['data']

            for row in rows:
                row = dict(zip(columns, row))
                conv_id = str(row['conversation_id'])
                
                msgcount = message_count.get(row['conversation_id'], 0)
                

                has_file = (
                    row['file_name'] is not None or
                    row['address'] is not None or
                    row['coordinates'] is not None or 
                    row['contact_phones'] is not None
                )

                message = {
                    'id': str(row['id']),
                    'text': row['text_content'],
                    'userId': row['sender_userid'],
                    'timestamp': row['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ') if row['created_at'] else None,
                    'type': row['message_type'],
                    'forwarded': bool(row['forwarded']),
                    'originalSenderId': row['originalSenderId'],
                    'originalTimestamp': row['originalTimestamp'].strftime('%Y-%m-%dT%H:%M:%SZ') if row['originalTimestamp'] else None,
                    'replyTo': row['reply_to_wamid'],
                    'wamid' : row['wamid'],
                    'is_read' : row['is_read'],
                    'read_at' : row['read_at'],
                    'status' : row['status'],
                    'errorText' : row['error_text'],
                    'file': {
                        'name': row['file_name'],
                        'size': row['file_size'],
                        'type': row['file_type'],
                        'preview': row['file_preview'],
                        'path': row['file_path'],
                        'thumbnail': None,
                        'duration': None,
                        'caption': row['file_caption'],
                        'address': row['address'],
                        'coordinates': row['coordinates'],
                    } if has_file else None,
                    'reactions': json.loads(row['reactions_json']) if isinstance(row['reactions_json'], str) else (row['reactions_json'] or {}),
                    'template': row['template'],
                    'msgcount' : msgcount
                }
                
                if row['contact_phones'] is not None and has_file is not None:
                    message['file']['contact'] = {
                        'name' : json.loads(row["contact_name"]) if isinstance(row["contact_name"], str) and row["contact_name"] is not None else (row["contact_name"] or {}),
                        'phones' : json.loads(row["contact_phones"]) if isinstance(row["contact_phones"], str) and row["contact_phones"] is not None else (row["contact_phones"] or {}),
                        'emails' : json.loads(row["contact_emails"]) if isinstance(row["contact_emails"], str) and row["contact_emails"] is not None else (row["contact_emails"] or {}),
                        'org' : json.loads(row["contact_org"]) if isinstance(row["contact_org"], str) and row["contact_org"] is not None else (row["contact_org"] or {}),
                    }

                if conv_id not in conversations:
                    conversations[conv_id] = []
                conversations[conv_id].append(message)
                response = {"data" : conversations, 'error' : False}
            
            return response
        except IndexError:
                data = {"conversations": {}}            
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get messages ", {"error": str(traceback.format_exc()), "response": response})    

        return response

    def save_conversation(self, data, type, owner_id, admin, wamid = ''):
        response = {"data" : [], 'error' : True}
        try:
            if not type:
                return {"data" : ['Message type is empty'], 'error' : True}
            
            if not owner_id or not admin:
                return {"data" : ['owner_id or admin is empty'], 'error' : True}

            user_id = data.get("to")
            if isinstance(user_id, list):
                user_id = user_id[0] if user_id else 0
            
            message = WhatsAppMessage(
                userid=user_id,
                message_type=type,
                template=data.get("components"),
                whatsapp_admin = owner_id,
                sender_userid =  admin,
                wa_timestamp = int(time.time()), 
                created_at = timezone.now(),  
                wamid = wamid or data.get("wamid", f"internal_{uuid.uuid4()}"),   
                is_read = 1,
                read_at = datetime.now(),
            )

            message.save()

            if message.pk is not None:
                return {"data" : [message.pk], 'error' : False}
            logger.app_logs("ERROR", "Failed to save_conversation ", {"error": message, "input": data})    
        except Exception as e:
            logger.app_logs("EXCEPTION", "Failed to save_conversation ", {"error": str(traceback.format_exc()), "response": response})    

        return response

    def save_message(self, validated_data: dict, owner_id, admin, wamid) -> WhatsAppMessage:
        """
        Inserts a message (and media if present) into the DB.
        validated_data = MessageSerializer.validated_data
        whatsapp_admin = WhatsAppAdminUser instance
        """
        msg_type  = validated_data["type"]
        file_data = validated_data.get("file")
        reply_to  = validated_data.get("replyTo")

        with transaction.atomic():

            # ── 1. Insert media (if present) ──────────────────────────────
            media_id = None
            if file_data and msg_type in ("image", "video", "audio", "document", "contact"):
                if msg_type == "contact":
                    parsed_size = 0.0
                else:
                    parsed_size = self.parse_size_mb(file_data.get("size", "0 MB"))

                media_data = {
                    "name": file_data.get("name", ""),
                    "size": parsed_size,
                    "type": file_data.get("type", ""),
                    "path": file_data.get("path", ""),
                    "preview": file_data.get("preview"),
                    "caption": file_data.get("caption", ""),
                    "duration": self.parse_float(file_data.get("duration", 0.0)),
                    "thumbnail": file_data.get("thumbnail", ""),
                }

                if msg_type == "contact" and "contact" in file_data:
                    contact_info = file_data["contact"]
                    media_data["contact_name"] = json.dumps(contact_info.get("name", {}))
                    media_data["contact_phones"] = json.dumps(contact_info.get("phones", []))
                    media_data["contact_emails"] = json.dumps(contact_info.get("emails", []))
                    media_data["contact_org"] = json.dumps(contact_info.get("org", {})) 

                media = WhatsAppMedia.objects.create(**media_data)
                media_id = media.id

            # ── 2. Location fields ────────────────────────────────────────
            address     = None
            coordinates = None
            if msg_type == "location" and file_data:
                address     = file_data.get("address")
                coords      = file_data.get("coordinates")    
                coordinates = json.dumps(coords) if coords else None

            user_id = validated_data["to"]
            if isinstance(user_id, list):
                user_id = user_id[0] if user_id else 0

            # ── 3. Insert message ─────────────────────────────────────────
            message = WhatsAppMessage.objects.create(
                wamid                = wamid,      
                userid               = user_id,
                sender_userid        = admin,
                #sender_phonenumber   = whatsapp_admin.phone_number,
                wa_timestamp         = int(time.time()),
                message_type         = msg_type,
                text_content         = validated_data.get("text") or None,
                reply_to_wamid       = reply_to,
                media_id             = media_id,
                address              = address,
                coordinates          = coordinates,
                whatsapp_admin       = owner_id,
                
            )

        return message


    def save_incoming_message(self, payload: dict, whatsapp_admin) -> WhatsAppMessage:
        """
        Inserts a message received from WhatsApp webhook.
        payload = raw parsed webhook message object.
        """
        msg_type = payload.get("type")

        with transaction.atomic():

            # ── 1. Insert media ───────────────────────────────────────────
            media_id = None
            media_payload = payload.get(msg_type)  

            if msg_type in ("image", "video", "audio", "document", "contact") and media_payload:
                media = WhatsAppMedia.objects.create(
                    name    = media_payload.get("filename") or f"{msg_type}_{int(time.time())}",
                    size    = 0.0,                             
                    type    = media_payload.get("mime_type", ""),
                    path    = media_payload.get("id", ""),   
                    preview = None,
                    caption = media_payload.get("caption", ""),
                )
                media_id = media.id

            # ── 2. Location ───────────────────────────────────────────────
            address     = None
            coordinates = None
            if msg_type == "location":
                loc         = payload.get("location", {})
                address     = loc.get("address") or loc.get("name")
                coordinates = json.dumps({"lat": loc["latitude"], "lng": loc["longitude"]})

            # ── 3. Forwarded context ──────────────────────────────────────
            forwarded_info   = payload.get("context", {})
            is_forwarded     = payload.get("forwarded", False)
            original_sender  = forwarded_info.get("forwarded_from")
            original_ts      = None  

            # ── 4. Reply context ──────────────────────────────────────────
            context       = payload.get("context", {})
            reply_to_wamid = context.get("id")  

            # ── 5. Insert message ─────────────────────────────────────────
            message = WhatsAppMessage.objects.create(
                wamid                = payload["id"],
                userid               = payload["_whatsapp_user_id"],  
                sender_userid        = payload.get("_whatsapp_user_id"),
                sender_phonenumber   = payload.get("from"),
                wa_timestamp         = int(payload["timestamp"]),
                message_type         = msg_type,
                text_content         = payload.get("text", {}).get("body") if msg_type == "text" else None,
                reply_to_wamid       = reply_to_wamid,
                media_id             = media_id,
                address              = address,
                coordinates          = coordinates,
                forwarded            = is_forwarded,
                originalSenderId     = original_sender,
                originalTimestamp    = original_ts,
                raw_webhook_payload  = payload,
                whatsapp_admin       = whatsapp_admin,
            )

        return message


    def save_reaction(self, message_id: int, user_id: int, emoji: str) -> WhatsAppReaction:
        """
        Upserts a reaction — replaces existing reaction by same user on same message.
        """
        reaction, _ = WhatsAppReaction.objects.update_or_create(
            message = message_id,
            user    = user_id,
            defaults = {"emoji": emoji}
        )
        return reaction


    def remove_reaction(self, message_id: int, user_id: int):
        """Deletes a reaction by a user on a message."""
        WhatsAppReaction.objects.filter(message=message_id, user=user_id).delete()


    def generate_wamid(self) -> str:
        """
        Generates a placeholder wamid for outgoing messages before the API responds.
        Replace with the actual wamid from the API response after sending.
        """
        import uuid
        return f"wamid.local_{uuid.uuid4().hex}"


    def update_wamid(self, message: WhatsAppMessage, real_wamid: str):
        """Call this after WhatsApp API responds with the real wamid."""
        WhatsAppMessage.objects.filter(id=message.id).update(wamid=real_wamid)


    def parse_size_mb(self, size_str: str) -> float:
        """Reuse from your serializer utils."""
        parts = size_str.strip().split()
        value, unit = float(parts[0]), parts[1].upper()
        return {"B": value/(1024**2), "KB": value/1024, "MB": value, "GB": value*1024}[unit]
    
    def parse_float(self, time:str) -> float:
        try:
            minutes, seconds = time.split(':')
            print(minutes, seconds)
            total_minutes = float(minutes) + (float(seconds) / 60)
            print(total_minutes)
            return total_minutes
        except:
            pass
        

    def get_conversations_page_json(self, data, conversation_id, offset=0, page_size=50):
        """
        Paginated messages for a single conversation using direct OFFSET.
 
        offset=0              → newest page_size messages (initial scroll trigger)
        offset=50             → the 50 before that
        offset=100            → the 10 before that (whatever remains)
 
        Accepts query params:  ?conversation_id=<id>&offset=<n>&page_size=50
 
        Returns:
            {
                "data":      [...messages...],  # oldest-first within the batch
                "has_more":  bool,
                "total":     int,
                "offset":    int,               # the offset used for this call
                "page_size": int,
                "error":     bool
            }
        """
        response = {"data": [], "has_more": False, "total": 0,
                    "offset": offset, "page_size": page_size, "error": True}
        try:
            admin_id = str(data.id.hex)
 
            # Total message count for this conversation
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM whatsapp_messages WHERE owner_id = %s AND userid = %s",
                    [admin_id, conversation_id]
                )
                total = cursor.fetchone()[0]
 
            sql = """
                SELECT
                    m.userid           AS conversation_id,
                    m.id,
                    m.text_content,
                    m.sender_userid,
                    m.created_at,
                    m.message_type,
                    m.forwarded,
                    m.originalSenderId,
                    m.originalTimestamp,
                    m.reply_to_wamid,
                    m.address,
                    m.coordinates,
                    m.template,
                    m.read_at,
                    m.is_read,
                    m.status,
                    m.error_text,
                    m.wa_timestamp,
                    f.name      AS file_name,
                    f.size      AS file_size,
                    f.type      AS file_type,
                    f.preview   AS file_preview,
                    f.caption   AS file_caption,
                    f.path      AS file_path,
                    f.contact_phones AS contact_phones,
                    f.contact_emails AS contact_emails,
                    f.contact_org AS contact_org,
                    f.contact_name AS contact_name,
                    r.reactions_json
                FROM whatsapp_messages m
                LEFT JOIN whatsapp_media f ON m.media_id = f.id
                LEFT JOIN (
                    SELECT
                        message,
                        JSON_OBJECTAGG(emoji, user_list) AS reactions_json
                    FROM (
                        SELECT message, emoji, JSON_ARRAYAGG(user) AS user_list
                        FROM WhatsPanel_whatsappreaction
                        GROUP BY message, emoji
                    ) rg
                    GROUP BY message
                ) r ON m.id = r.message
                WHERE m.owner_id = %s AND m.userid = %s
                ORDER BY m.wa_timestamp DESC
                LIMIT %s OFFSET %s
            """
 
            with connection.cursor() as cursor:
                cursor.execute(sql, [admin_id, conversation_id, page_size, offset])
                columns = [col[0] for col in cursor.description]
                rows    = cursor.fetchall()
 
            messages = []
            for row in rows:
                row      = dict(zip(columns, row))
                has_file = (
                    row["file_name"]      is not None
                    or row["address"]     is not None
                    or row["coordinates"] is not None
                    or row['contact_phones'] is not None
                )
                is_read = (
                    row["read_at"] is not None
                    or str(row["sender_userid"]) == admin_id
                )
                message = {
                    "id":                str(row["id"]),
                    "text":              row["text_content"],
                    "userId":            row["sender_userid"],
                    "timestamp":         row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["created_at"] else None,
                    "type":              row["message_type"],
                    "forwarded":         bool(row["forwarded"]),
                    "originalSenderId":  row["originalSenderId"],
                    "originalTimestamp": row["originalTimestamp"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["originalTimestamp"] else None,
                    "replyTo":           row["reply_to_wamid"],
                    "is_read":           row['is_read'],
                    "read_at":           row["read_at"],
                    "status":            row["status"],
                    "errorText":        row["error_text"],
                    "file": {
                        "name":        row["file_name"],
                        "size":        row["file_size"],
                        "type":        row["file_type"],
                        "preview":     row["file_preview"],
                        "path":        row["file_path"],
                        "thumbnail":   None,
                        "duration":    None,
                        "caption":     row["file_caption"],
                        "address":     row["address"],
                        "coordinates": row["coordinates"],
    
                    } if has_file else None,
                    "reactions": json.loads(row["reactions_json"]) if isinstance(row["reactions_json"], str) else (row["reactions_json"] or {}),
                    "template":  row["template"],
                }
                
                if row['contact_phones'] and has_file is not None:
                    message['file']['contact'] = {
                        'name' : json.loads(row["contact_name"]) if isinstance(row["contact_name"], str) and row["contact_name"] is not None else (row["contact_name"] or {}),
                        'phones' : json.loads(row["contact_phones"]) if isinstance(row["contact_phones"], str) and row["contact_phones"] is not None else (row["contact_phones"] or {}),
                        'emails' : json.loads(row["contact_emails"]) if isinstance(row["contact_emails"], str) and row["contact_emails"] is not None else (row["contact_emails"] or {}),
                        'org' : json.loads(row["contact_org"]) if isinstance(row["contact_org"], str) and row["contact_org"] is not None else (row["contact_org"] or {}),
                    }
                messages.append(message)
            messages.reverse()
 
            actual_fetched = len(messages)
            response = {
                "data":      messages,
                "has_more":  (offset + actual_fetched) < total,  # safe: uses actual count
                "total":     total,
                "offset":    offset,
                "page_size": page_size,
                "error":     False,
            }
 
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get paged messages",
                            {"error": str(traceback.format_exc())})
        return response
    
    def mark_messages_read(self, data, conversation_id = None, read_at = None, wamid = None):
        """
        Mark all unread incoming messages in a conversation as read.
        Called when the admin opens/focuses a conversation.
        """
        try:
            with connection.cursor() as cursor:
                if (wamid != None and read_at != None):
                    res = cursor.execute("""
                        UPDATE whatsapp_messages
                        SET is_read = %s,
                        read_at = %s
                        WHERE owner_id = %s
                        AND wamid  = %s
                        AND read_at IS NULL    
                        AND is_read IS FALSE
                    """, [
                        True,
                        read_at,
                        data.id.hex,         
                        wamid,
                    ])
                else:
                    res = cursor.execute("""
                        UPDATE whatsapp_messages
                        SET is_read = %s,
                        read_at = %s
                        WHERE owner_id = %s
                        AND userid = %s
                        AND sender_userid = %s   
                        AND read_at IS NULL    
                        AND is_read IS FALSE
                    """, [
                        True,
                        timezone.now(),
                        data.id.hex,         
                        conversation_id,     
                        data.owner_id,       
                    ])
                
                if cursor.rowcount > 0:
                    return {"data": None, "error": False}
                else:
                    return {"data": res, "error": True}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to mark messages read",
                            {"error": str(traceback.format_exc())})
            return {"data": False, "error": True}
        

    def count_message(self, owner_id):
        try:
            data = None
            with connection.cursor() as cursor:
                cursor.execute("""
                    select userid, count(*) as msgcount
                    from whatsapp_messages 
                    where owner_id=%s group by userid;
                """, [owner_id])    

                rows = cursor.fetchall()
                if rows:
                    data = {row[0]: row[1] for row in rows}

            return {"data": data, "error": False}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get count_message",
                            {"error": str(traceback.format_exc())})
            return {"data": False, "error": True}
        
    def select_message(self, owner_id, wamid):
        try:
            data = None
            with connection.cursor() as cursor:
                cursor.execute("""
                    select id from whatsapp_messages 
                    where owner_id=%s and wamid=%s 
                """, [owner_id, wamid])    

                row = cursor.fetchone()
                if row:
                    data = {"id": row[0]}
                else:
                    data = None
            
            return {"data": data, "error": False}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to get select_message", {"error": str(traceback.format_exc())})
            return {"data": False, "error": True}
        

    def insert_whatsapp_message(self, payload, owner_id):
        try:
            with transaction.atomic():
                media_id = None
                if payload.get("file") and payload['type'] != 'location':
                    file_data = payload["file"]
                    contact = file_data.get('contact', {})
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO whatsapp_media
                                (name, size, type, preview, caption, path, thumbnail, duration, contact_phones, contact_emails, contact_org, contact_name)
                            VALUES
                                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            file_data.get("name"),
                            file_data.get("size") or 0,
                            file_data.get("type"),
                            file_data.get("preview"),
                            file_data.get("caption"),
                            file_data.get("path"),
                            file_data.get("thumbnail"),
                            file_data.get("duration"),
                            json.dumps(contact.get("phones")) if contact.get("phones") else None,
                            json.dumps(contact.get("emails")) if contact.get("emails") else None,
                            json.dumps(contact.get("org")) if contact.get("org") else None,
                            json.dumps(contact.get("name")) if contact.get("name") else None,
                        ))
                        media_id = cursor.lastrowid

                try:
                    dt = datetime.fromisoformat(payload["timestamp"])
                    wa_timestamp = int(dt.timestamp())
                except (TypeError, ValueError):
                    wa_timestamp = 0

                reactions = payload.get("reactions")
                if not reactions:
                    address = coordinates = None
                    if payload['type'] == 'location':
                        file_data = payload["file"]
                        address = file_data.get('address')
                        coordinates = file_data.get('coordinates')
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO whatsapp_messages
                                (userid, wamid, text_content, sender_userid, message_type,
                                forwarded, originalSenderId, originalTimestamp, reply_to_wamid,
                                media_id, created_at, read_at, owner_id, wa_timestamp, address, coordinates)
                            VALUES
                                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            payload["sender_id"],
                            payload["wamid"],
                            payload["text"],
                            payload["sender_id"],
                            payload["type"],
                            payload["forwarded"],
                            0,
                            payload["originalTimestamp"],
                            payload["reply_to_wamid"],
                            media_id,
                            timezone.now(),       
                            None,                       
                            owner_id,
                            wa_timestamp,          
                            address,
                            coordinates,
                        ))
                        message_id = cursor.lastrowid

                if payload.get("reactions"):
                    WhatsAppMessageQueryModel = WhatsAppMessageQuery()
                    owner_id = str(owner_id).replace('-', '')
                    message_id_resp = WhatsAppMessageQueryModel.select_message(owner_id, payload["reply_to_wamid"])
                    if ('error' in message_id_resp and message_id_resp['error']):
                        logger.app_logs("ERROR", "Failed to get message id to save reaction", {"error": message_id_resp['error'], "response": message_id_resp})
                        
                    if ('data' in message_id_resp and message_id_resp['data'] and message_id_resp['data']['id'] is None):
                        logger.app_logs("ERROR", "Message not found in DB to save reaction", {"error": message_id_resp, "inputData": message_id})

                    message_id = message_id_resp['data']['id'] or -1

                    with connection.cursor() as cursor:
                        for emoji, user_list in payload["reactions"].items():
                            for user in user_list:
                                cursor.execute("""
                                    INSERT INTO WhatsPanel_whatsappreaction (message, emoji, user)
                                    VALUES (%s, %s, %s)
                                """, (message_id, emoji, user))

            return {"success": True, "message_id": message_id}

        except Exception as e:
            logger.app_logs("ERROR", "Failed to insert WhatsApp message", {"error": str(traceback.format_exc()), "payload": payload})
            return {"success": False, "error": str(e)}

        
    def update_message(self, status, error_text, owner_id, wamid):
        try:
            data = None
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE whatsapp_messages 
                    SET status=%s, error_text=%s
                    WHERE owner_id=%s AND wamid=%s 
                """, [status, error_text, owner_id, wamid])    
                if cursor.rowcount > 0:
                    
                    data = {"wamid": wamid} 
                else:
                    data = None

            return {"data": data, "error": False}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to update_message", {"error": str(traceback.format_exc())})
            return {"data": False, "error": True}