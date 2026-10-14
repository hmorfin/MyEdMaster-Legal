import logging
import time

import httpx
import fitz
import boto3
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


class PDFExtractor:

    def _get_presigned_url(self, storage_path: str) -> str:
        # Note: storage_path (the S3 key) is an internal document identifier, not
        # PII — safe to log. The generated presigned URL itself is NOT logged since
        # it is a short-lived, unauthenticated bearer credential for the object.
        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.s3_region,
            )
            return s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.s3_bucket_name,
                    "Key":    storage_path,
                },
                ExpiresIn=settings.s3_presign_expires_seconds,
            )
        except ClientError:
            logger.error("s3_presign_failed", exc_info=True, extra={"storage_path": storage_path})
            raise RuntimeError("Failed to generate presigned URL")

    def extract_from_storage_path(self, storage_path: str) -> str:
        url = self._get_presigned_url(storage_path)
        return self.extract_from_url(url)

    def extract_from_url(self, url: str) -> str:
        start = time.time()
        try:
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.error("pdf_fetch_failed", exc_info=True)
            raise RuntimeError("Failed to fetch PDF")

        text = self._extract_from_bytes(response.content)
        logger.info(
            "pdf_fetched_and_extracted",
            extra={
                "bytes_downloaded": len(response.content),
                "extracted_text_length": len(text),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )
        return text

    def extract_from_path(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
        except FileNotFoundError:
            logger.error("pdf_not_found", extra={"file_path": file_path})
            raise RuntimeError("PDF not found at the given path")

        return self._extract_from_bytes(pdf_bytes)

    def _extract_from_bytes(self, pdf_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            logger.error("pdf_parse_failed", exc_info=True)
            raise RuntimeError("Could not parse PDF")

        pages_text = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                pages_text.append(f"[Page {page_num}]\n{text.strip()}")

        page_count = doc.page_count
        doc.close()

        if not pages_text:
            logger.warning("pdf_no_extractable_text", extra={"total_pages": page_count})
            raise RuntimeError(
                "PDF appears to be empty or image-only (no extractable text)."
            )

        return "\n\n".join(pages_text)


extractor = PDFExtractor()