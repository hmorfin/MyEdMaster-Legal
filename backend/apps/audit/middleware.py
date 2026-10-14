import logging
import time

logger = logging.getLogger("audit")


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = round((time.time() - start) * 1000)

        user = (
            request.user.username
            if hasattr(request, "user") and request.user.is_authenticated
            else "anonymous"
        )

        logger.info(
            "%s %s %s %dms user=%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            user,
        )
        return response