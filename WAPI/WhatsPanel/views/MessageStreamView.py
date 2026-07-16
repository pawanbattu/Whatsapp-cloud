import json
import time
from django.views import View
from django.http import StreamingHttpResponse
from WhatsPanel.models import *
from django.conf import settings
import pika
from core.logger import app_logs
import traceback

class MessageStreamView(View):
    def get(self, request, admin_id, *args, **kwargs):
        response = StreamingHttpResponse(
            self.event_generator(admin_id),
            content_type='text/event-stream'
        )

        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'

        return response
    
    def event_generator(self, admin_id):
        connection = None
        try:
            params = pika.URLParameters(settings.CELERY_BROKER_URL)
            params.heartbeat = 30
            params.blocked_connection_timeout = 30

            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            exchange_name = f'whatsapp_stream_{admin_id}'
            channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')

            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange=exchange_name, queue=queue_name)

            for method_frame, properties, body in channel.consume(queue_name, inactivity_timeout=15):
                if body:
                    payload = body.decode('utf-8')
                    yield f"data: {payload}\n\n"
                    channel.basic_ack(method_frame.delivery_tag)
                else:
                    yield ": keepalive\n\n"

        except GeneratorExit:
            # client disconnected / tab closed — normal, not an error
            app_logs("INFO", "SSE client disconnected for admin", {admin_id})
            raise
        except Exception:
            app_logs("ERROR", "SSE stream crashed for admin", {"admin_id": admin_id, "error":  str(traceback.format_exc())})
        finally:
            try:
                if connection and connection.is_open:
                    connection.close()
            except Exception:
                app_logs("EXCEPTION", "Error closing pika connection for admin", {"admin_id": admin_id, "error":  str(traceback.format_exc())})
    
    # def event_generator(self, admin_id):
    #     connection = pika.BlockingConnection(pika.URLParameters(settings.CELERY_BROKER_URL))
    #     channel = connection.channel()
        
    #     # Declare the same fanout exchange
    #     exchange_name = f'whatsapp_stream_{admin_id}'
    #     channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')

    #     # Create an exclusive, temporary queue for this specific HTTP request
    #     result = channel.queue_declare(queue='', exclusive=True)
    #     queue_name = result.method.queue
    #     channel.queue_bind(exchange=exchange_name, queue=queue_name)

    #     try:
    #         for method_frame, properties, body in channel.consume(queue_name, inactivity_timeout=15):
    #             if body:
    #                 payload = body.decode('utf-8')
    #                 yield f"data: {payload}\n\n"

    #                 channel.basic_ack(method_frame.delivery_tag)
    #             else:
    #                 yield ": keepalive\n\n"
                    
    #     except GeneratorExit:
    #         if connection.is_open:
    #             connection.close()

    # def event_generator(self, admin_id):
    #     count = 0

    #     while True:
    #         count += 1
    #         id = 900+count
    #         payload = json.dumps({
    #         "id": id,
    #         "text": "Hey David! I wanted to share this amazing article I just read.",
    #         "userId": 14,
    #         "timestamp": "2024-01-15T13:00:00Z",
    #         "type": "file",
    #         "sender_id": 14,
    #         "file": {
    #             "name": "blockchain-article.pdf",
    #             "size": "3.1 MB",
    #             "type": "pdf",
    #             "caption": (
    #                 "This explains the new blockchain protocol "
    #                 "in simple terms - thought you'd appreciate it!"
    #             )
    #         },
    #         "reactions": {}
    #         })
    #         yield f"data: {payload}\n\n"

    #         time.sleep(2)
    #     last_id = 0

    #     while True:
    #         new_msgs = WhatsAppMessage.objects.filter(
    #             whatsapp_admin=admin_id,
    #             id__gt=last_id
    #         ).order_by('id')

    #         for msg in new_msgs:
    #             last_id = msg.id

    #             payload = json.dumps({
    #                 'id': msg.id,
    #                 'sender_id': msg.sender_id,
    #                 'receiver_id': msg.receiver_id,
    #                 'text': msg.text,
    #                 'type': msg.msg_type,
    #                 'timestamp': msg.created_at.isoformat(),
    #             })

    #             yield f"data: {payload}\n\n"

    #         time.sleep(1)