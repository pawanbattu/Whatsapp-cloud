import os, uuid, shutil
from django.conf import settings

BASE_UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "chunk_uploads")
TEMP_DIR = os.path.join(BASE_UPLOAD_DIR, "temp")
FINAL_DIR = os.path.join(BASE_UPLOAD_DIR, "completed")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

def get_upload_temp_dir(upload_id):
    path = os.path.join(TEMP_DIR, upload_id)
    os.makedirs(path, exist_ok=True)
    return path

def merge_chunks(upload_id, filename):
    temp_dir = get_upload_temp_dir(upload_id)
    final_path = os.path.join(FINAL_DIR, filename)
    with open(final_path, "wb") as final_file:
        chunk_files = sorted(
            [f for f in os.listdir(temp_dir) if f.startswith("chunk_")],
            key=lambda x: int(x.split("_")[1])
        )
        for chunk_name in chunk_files:
            chunk_path = os.path.join(temp_dir, chunk_name)
            with open(chunk_path, "rb") as cf:
                shutil.copyfileobj(cf, final_file)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return final_path
