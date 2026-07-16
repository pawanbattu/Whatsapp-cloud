import time
import uuid
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from WhatsPanel.models import *
import core.logger as logger
import traceback
import datetime


class ScheduledMessageQuery():

    def __init__(self):
        pass

    def insert_schedule_message(self, payload, admin_user, admin, msg_type):
        response = {"data" : [], 'error' : True}
        try:
            scheduled_time = payload.get('scheduled_at')

            if not isinstance(scheduled_time, datetime.datetime):
                raise ValueError("Invalid or missing scheduled_at datetime.")

            if timezone.is_naive(scheduled_time):
                scheduled_time = timezone.make_aware(scheduled_time, timezone.utc)

            current_wa_timestamp = int(time.time())
            messages_to_insert = []

            for recipient_id in payload.get('to', []):
                admin_config = WhatsAppUser.objects.get(id=recipient_id)
                if not admin_config:
                    continue
                msg = ScheduledMessage(
                    userid=recipient_id,
                    sender_userid=admin, 
                    wa_timestamp=current_wa_timestamp,
                    message_type=msg_type,
                    text_content=payload.get('text'),
                    file=payload.get('file'),
                    template = str(payload),
                    scheduled_at=scheduled_time,
                    status='PENDING',
                    whatsapp_admin=admin_user 
                )
                messages_to_insert.append(msg)

            if messages_to_insert:
                ScheduledMessage.objects.bulk_create(messages_to_insert)

                return {"data" : ['done'], 'error' : False}
            
            return {"data" : [messages_to_insert], 'error' : True}
        except Exception as e:
            logger.app_logs("ERROR", "Failed to schedule message ", {"error": str(traceback.format_exc()), "response": response})    

            return response
        
    def get_schedule_message(self, admin_user, offset=0, limit=50):
        response = {"data": [], "error": True}

        try:
            if not admin_user:
                return {"data": [], "error": False}

            try:
                offset = int(offset)
                limit = int(limit)
            except (TypeError, ValueError):
                offset = 0
                limit = 50

            queryset = ScheduledMessage.objects.filter(
                whatsapp_admin=admin_user
            ).order_by("-created_at")

            
            page = list(queryset.values()[offset: offset + limit + 1])

            has_more = len(page) > limit
            scheduled_messages = page[:limit]

            return {
                "data": scheduled_messages,
                "has_more": has_more,
                "error": False
            }

        except Exception:
            logger.app_logs(
                "ERROR",
                "Failed to get scheduled messages",
                {"error": traceback.format_exc(), "response": response},
            )
            return response