from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import json
import pika
from django.conf import settings
from core.logger import app_logs
import traceback
import time


_connection = None
_channel = None

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response({
            'success': False,
            'errors': 'Internal Server Error',
            'status_code': 500,
            'detail': str(exc) 
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    errors = response.data
    if isinstance(errors, dict):
        flat_errors = {
            key: (value[0] if isinstance(value, list) and len(value) == 1 else value)
            for key, value in errors.items()
        }
    else:
        flat_errors = errors

    response.data = {
        'success': False,
        'errors': flat_errors,
        'status_code': response.status_code,
    }

    return response

def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """Standardized success response."""
    payload = {'success': True}
    if message:
        payload['message'] = message
    if data is not None:
        payload['data'] = data
    return Response(payload, status=status_code)


def error_response(
    error=None,
    message=None,
    status_code=status.HTTP_400_BAD_REQUEST
):
    """Fully generalized error response."""

    payload = {
        "success": False,
        "status_code": status_code
    }

    def extract_message(err):
        """Try to extract best possible message."""
        if isinstance(err, str):
            return err

        if isinstance(err, dict):
            for key in ["message", "detail", "error", "msg"]:
                val = err.get(key)
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    return extract_message(val)

        if isinstance(err, list) and err:
            return extract_message(err[0])

        return str(err)

    def normalize_errors(err):
        """Flatten/clean error structure."""
        if isinstance(err, dict):
            normalized = {}
            for k, v in err.items():
                if isinstance(v, list):
                    normalized[k] = v[0] if len(v) == 1 else v
                elif isinstance(v, dict):
                    normalized[k] = normalize_errors(v)
                else:
                    normalized[k] = v
            return normalized

        elif isinstance(err, list):
            return [normalize_errors(e) for e in err]

        return err

    final_message = message or extract_message(error)
    normalized_error = normalize_errors(error) if error else None

    if final_message:
        payload["message"] = final_message

    if normalized_error:
        payload["errors"] = normalized_error

    return Response(payload, status=status_code)



# def publish_to_stream(admin_id, payload):
#     try:
#         """Publishes the formatted JSON payload to RabbitMQ."""
#         # Update with your RabbitMQ connection parameters (from settings)
#         connection = pika.BlockingConnection(pika.URLParameters(settings.CELERY_BROKER_URL))
#         channel = connection.channel()
        
#         # We use a 'fanout' exchange so multiple open frontend tabs can all receive the message
#         exchange_name = f'whatsapp_stream_{admin_id}'
#         channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')

#         channel.basic_publish(
#             exchange=exchange_name,
#             routing_key='',
#             body=json.dumps(payload)
#         )
#         connection.close()
#     except Exception as e:
#         app_logs("ERROR", "Failed to get process recieving message ", {"error": str(traceback.format_exc()), "inputData":payload})
#         raise

def publish_to_stream(admin_id, payload, max_retries=3):
    """
    Publishes the formatted JSON payload to RabbitMQ (fanout exchange)
    so open frontend tabs get a live update. Best-effort: failure here
    should not crash the caller, since the message is already persisted.
    """
    body = json.dumps(payload, default=str)
    exchange_name = f'whatsapp_stream_{admin_id}'

    for attempt in range(1, max_retries + 1):
        connection = None
        try:
            params = pika.URLParameters(settings.CELERY_BROKER_URL)
            params.socket_timeout = 5
            params.blocked_connection_timeout = 5

            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.confirm_delivery()

            channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')

            channel.basic_publish(
                exchange=exchange_name,
                routing_key='',
                body=body,
            )

            return 

        except (pika.exceptions.AMQPConnectionError,
                 pika.exceptions.AMQPChannelError,
                 pika.exceptions.UnroutableError) as e:

            app_logs("ERROR", "RabbitMQ publish attempt %d/%d failed for admin %s: %s", {attempt, max_retries, admin_id, e})
            if attempt == max_retries:
                app_logs("EXCEPTION", "Giving up publishing stream message for admin %s: %s", {"error": traceback.format_exc(), "inputData": payload , "admin_id" : admin_id})
                return  
            time.sleep(0.5 * attempt) 

        except Exception:
            app_logs("EXCEPTION", "Unexpected error publishing stream message for admin %s: %s", {"error": traceback.format_exc(), "inputData": payload, "admin_id" : admin_id})
            return 

        finally:
            if connection and connection.is_open:
                connection.close()

def is_json_serializable(my_object):
    try:
        json.dumps(my_object)
        return True
    except TypeError:
        return False