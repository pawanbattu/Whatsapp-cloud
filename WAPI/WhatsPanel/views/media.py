import uuid
import os
from minio import Minio
from minio.error import S3Error
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from WhatsPanel.models import *
from WhatsPanel.serializer.MediaSerializer import (
    StartUploadSerializer, UploadChunkSerializer,
    CompleteUploadSerializer, CancelUploadSerializer
)
from core.file_utils import get_upload_temp_dir, merge_chunks
from datetime import timedelta

minio_client = Minio(
    endpoint=getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000'),
    access_key=getattr(settings, 'MINIO_ACCESS_KEY', 'minio'),
    secret_key=getattr(settings, 'MINIO_SECRET_KEY', 'minio123'),
    secure=getattr(settings, 'MINIO_SECURE', False),   
    # region="us-east-1"
)

MINIO_BUCKET = getattr(settings, 'MINIO_BUCKET', 'whatsappmedia')
MINIO_ENDPOINT = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000'),
MINIO_URL = getattr(settings, 'MINIO_URL', 'http://localhost') 

def _ensure_bucket():
    """Create the bucket if it does not exist yet."""
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


# ---------------------------------------------------------------------------
# Chunked-upload views (unchanged logic, still reassemble on disk)
# ---------------------------------------------------------------------------

class StartChunkUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()
        data['upload_id'] = str(uuid.uuid4())
        serializer = StartUploadSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'upload_id': serializer.data['upload_id'],
                'total_chunks': serializer.data['total_chunks']
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadChunkView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UploadChunkSerializer(data=request.data)
        if serializer.is_valid():
            upload_id = serializer.validated_data['upload_id']
            chunk_index = serializer.validated_data['chunk_index']
            chunk = serializer.validated_data['chunk']

            temp_dir = get_upload_temp_dir(upload_id)
            chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
            with open(chunk_path, 'wb+') as destination:
                for chunk_part in chunk.chunks():
                    destination.write(chunk_part)

            ChunkedUpload.objects.filter(upload_id=upload_id).update(
                uploaded_chunks=models.F('uploaded_chunks') + 1
            )

            return Response({'success': True, 'chunk_index': chunk_index})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompleteChunkUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CompleteUploadSerializer(data=request.data)
        if serializer.is_valid():
            upload_id = serializer.validated_data['upload_id']
            filename = serializer.validated_data['filename']

            upload = ChunkedUpload.objects.filter(upload_id=upload_id).first()
            if not upload:
                return Response({'error': 'Invalid upload_id'}, status=404)

            # Reassemble chunks into a single file on disk
            final_path = merge_chunks(upload_id, filename)

            # Upload the reassembled file to MinIO
            try:
                _ensure_bucket()
                object_name = f"chunk_uploads/{upload_id}/{filename}"
                minio_client.fput_object(
                    bucket_name=MINIO_BUCKET,
                    object_name=object_name,
                    file_path=final_path,
                    content_type=upload.file_type or 'application/octet-stream',
                )
            except S3Error as exc:
                return Response(
                    {'error': 'MinIO upload failed', 'details': str(exc)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            upload.completed = True
            upload.save()

            # Build a presigned URL (valid for 7 days) so the frontend can use it
            # file_url = minio_client.presigned_get_object(
            #     bucket_name=MINIO_BUCKET,
            #     object_name=object_name,
            #     expires=timedelta(hours=24)

            # )
            file_url = file_url = f"{MINIO_URL}/{MINIO_BUCKET}/{object_name}"
            media_type = (upload.file_type or '').split('/')[0]

            return Response({
                'fileUrl': file_url,
                'mediaType': media_type,
                'objectName': object_name,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CancelChunkUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CancelUploadSerializer(data=request.data)
        if serializer.is_valid():
            upload_id = serializer.validated_data['upload_id']
            upload = ChunkedUpload.objects.filter(upload_id=upload_id).first()
            if upload:
                upload.delete()
                temp_dir = get_upload_temp_dir(upload_id)
                if os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
            return Response({'success': True})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Single-file upload — now goes straight to MinIO instead of WhatsApp Graph API
# ---------------------------------------------------------------------------

class WhatsAppMediaUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        object_name = f"uploads/{uuid.uuid4()}_{file_obj.name}"

        try:
            _ensure_bucket()

            minio_client.put_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name,
                data=file_obj,
                length=file_obj.size,
                content_type=file_obj.content_type or 'application/octet-stream',
            )

            # Presigned URL valid for 7 days (adjust expires as needed)
            # from datetime import timedelta
            # file_url = minio_client.presigned_get_object(
            #     bucket_name=MINIO_BUCKET,
            #     object_name=object_name,
            #     expires=timedelta(days=7),
            # )

            file_url = file_url = f"{MINIO_URL}/{MINIO_BUCKET}/{object_name}"

            media_type = (file_obj.content_type or '').split('/')[0]

            return Response({
                'success': True,
                'fileUrl': file_url,
                'objectName': object_name,
                'mediaType': media_type,
            })

        except S3Error as exc:
            return Response(
                {'error': 'MinIO upload failed', 'details': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        



# class WhatsAppMediaUploadView(APIView):

#     permission_classes = [AllowAny]
#     # Enable file uploads in DRF
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request, *args, **kwargs):
#         file_obj = request.FILES.get('file')
        
#         if not file_obj:
#             return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

#         # Credentials (store these in your settings.py or .env)
#         # NOTE: You need the APP ID (not Business ID) and a valid Access Token
#         ACCESS_TOKEN = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN')
#         APP_ID = getattr(settings, 'FACEBOOK_APP_ID', 'YOUR_APP_ID')
#         VERSION = 'v21.0'

#         try:
#             # --- STEP 1: Initialize Upload Session ---
#             # We tell Meta how big the file is and what type it is
#             init_url = f"https://graph.facebook.com/{VERSION}/{APP_ID}/uploads"
            
            
#             init_params = {
#                 'file_length': file_obj.size,
#                 'file_type': file_obj.content_type, # e.g. 'image/jpeg'
#                 'access_token': ACCESS_TOKEN
#             }

#             init_res = requests.post(init_url, params=init_params)
            
#             if init_res.status_code != 200:
#                 return Response({
#                     "error": "Failed to initialize upload session",
#                     "details": init_res.json()
#                 }, status=init_res.status_code)

#             session_id = init_res.json().get('id')

#             # --- STEP 2: Upload Binary Data ---
#             # We send the actual file content to the session ID URL
#             upload_url = f"https://graph.facebook.com/{VERSION}/{session_id}"
            
#             headers = {
#                 'Authorization': f'OAuth {ACCESS_TOKEN}',
#                 'file_offset': '0'
#             }

#             # file_obj.read() gets the binary content
#             upload_res = requests.post(
#                 upload_url, 
#                 headers=headers, 
#                 data=file_obj.read() 
#             )

#             if upload_res.status_code != 200:
#                 return Response({
#                     "error": "Failed to upload file content",
#                     "details": upload_res.json()
#                 }, status=upload_res.status_code)

#             result = upload_res.json()
            
#             # Return the "h" handle to the frontend
#             return Response({
#                 "success": True,
#                 "handle": result.get('h')
#             })

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)