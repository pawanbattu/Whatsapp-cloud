from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    view = context.get('view', None)
    logger.error(f"Error in {view}: {exc}", exc_info=True)

    if response is not None:
        return Response({
            'status': 'error',
            'error_code': response.status_code,
            'message': response.data.get('detail', 'Unexpected error'),
        }, status=response.status_code)
    else:
        return Response({
            'status': 'error',
            'error_code': 500,
            'message': str(exc),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
