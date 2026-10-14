from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, parsers
from .serializers import DocumentUploadSerializer
from .services import CloudStorageService
from apps.users.models import UserProfile
from .models import UserDocument

class DocumentView(APIView):
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)
    def post(self, request, user_id):
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                try:
                    user = UserProfile.objects.get(id=user_id)
                except UserProfile.DoesNotExist:
                    return Response({"status": "error", "message": "User not found"}, status=404)
                storage_path = CloudStorageService.upload_document(
                    user_id=user_id,
                    user_name=user.first_name.replace(" ",""),
                    file_obj=request.FILES['file']
                )
                doc = serializer.save(
                    user=user,
                    file_name=request.FILES['file'].name,
                    storage_path=storage_path,
                    file_size=request.FILES['file'].size
                )
                return Response({
                    "status": "success",
                    "data": {
                        "document_id": str(doc.id),
                        "file_name": doc.file_name,
                        "storage_path": doc.storage_path
                    }
                }, status=status.HTTP_201_CREATED)     
            except Exception as e:
                return Response({"status": "error", "message": f"Storage error: {str(e)}"}, status=500)
        return Response({"status": "error", "errors": serializer.errors}, status=400)

    def get(self, request, user_id):
        try:
            documents = UserDocument.objects.filter(user_id=user_id)
            if not documents.exists():
                return Response({
                    "status": "success",
                    "data": [],
                    "message": "No documents found for this user."
                }, status=status.HTTP_200_OK)
            doc_list = []
            for doc in documents:
                doc_list.append({
                    "document_id": str(doc.id),
                    "file_name": doc.file_name,
                    "file_size": doc.file_size,
                    "upload_date": doc.upload_date,
                    "status": getattr(doc, 'status', 'uploaded'),
                    "download_url": CloudStorageService.get_download_url(doc.storage_path)
                })
            return Response({
                "status": "success",
                "count": len(doc_list),
                "data": doc_list
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)