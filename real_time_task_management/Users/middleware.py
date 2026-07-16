from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str):
    try:
        token = AccessToken(token_str)
        return User.objects.get(id=token["user_id"])
    except (TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Reads the JWT access token from the 'Authorization: Bearer <token>'
    header during the WebSocket handshake and sets scope["user"].
    """
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")

        if auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ", 1)[1]
        else:
            token_str = auth_header

        if token_str:
            scope["user"] = await get_user_from_token(token_str)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
