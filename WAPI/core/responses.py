from rest_framework.response import Response

def response(data=None, message="Success", status_code=200, error=False):
    return Response({
        "status": "error" if error else "success",
        "error_code": status_code if error else 0,
        "message": message,
        "data": data
    }, status=status_code)
