from rest_framework import serializers
from .models import UserDocument
import struct

# apps/docs/serializers.py

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PAGE_COUNT = 50

PDF_MAGIC_BYTES = b"%PDF"


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = UserDocument
        fields = ['id', 'file', 'file_name', 'storage_path', 'upload_date']
        read_only_fields = ['id', 'user', 'file_name', 'storage_path', 'upload_date']

    def create(self, validated_data):
        validated_data.pop('file', None)
        return super().create(validated_data)

    def validate_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are accepted.")

        if value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError(
                f"File size exceeds the {MAX_FILE_SIZE_MB}MB limit."
            )

        header = value.read(4)
        value.seek(0)
        if header != PDF_MAGIC_BYTES:
            raise serializers.ValidationError(
                "Invalid file content. Only real PDF files are accepted."
            )

        try:
            content = value.read()
            value.seek(0)
            page_count = content.count(b"/Page\n") + content.count(b"/Page\r") + content.count(b"/Page ")
            if page_count > MAX_PAGE_COUNT:
                raise serializers.ValidationError(
                    f"PDF exceeds the {MAX_PAGE_COUNT} page limit."
                )
        except serializers.ValidationError:
            raise
        except Exception:
            pass 

        return value