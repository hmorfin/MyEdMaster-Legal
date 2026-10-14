from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import shortuuid
import hashlib

class CloudStorageService:

    @staticmethod
    def upload_document(user_id, user_name, file_obj, existing_path=None):
        print(f"DEBUG: Storage Bucket -> {default_storage.bucket_name}")
        if existing_path:
            # Overwrite existing file at same path
            if default_storage.exists(existing_path):
                default_storage.delete(existing_path)
            path = default_storage.save(existing_path, file_obj)
            return path
        # New upload — generate unique path
        user_hash = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:8]
        doc_uuid = shortuuid.ShortUUID().random(length=5)
        full_path = f"{user_name}-{user_hash}/{doc_uuid}-{file_obj.name}".lower()
        print(f'file name: {full_path}')
        path = default_storage.save(full_path, file_obj)
        return path

    @staticmethod
    def get_download_url(storage_path):
        return default_storage.url(storage_path)

    @staticmethod
    def get_presigned_url(storage_path, expiration=3600):
        return default_storage.url(storage_path)