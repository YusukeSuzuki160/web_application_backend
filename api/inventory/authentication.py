from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def get_header(self, request: Request) -> bytes:
        token = request.COOKIES.get("access")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        refresh = request.COOKIES.get("refresh")
        request.META["HTTP_REFRESH_TOKEN"] = refresh
        return super().get_header(request)