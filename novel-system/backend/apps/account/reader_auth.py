"""Front-end reader auth (v87) — register/login/JWT for reader accounts."""
from __future__ import annotations
import hashlib, secrets, time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"

def _verify_password(password: str, stored: str) -> bool:
    if "$" not in stored: return False
    salt, hash_val = stored.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hash_val

def _generate_token(reader_id: int) -> str:
    payload = f"{reader_id}:{int(time.time())}:{secrets.token_hex(16)}"
    return hashlib.sha256(payload.encode()).hexdigest()

@api_view(["POST"])
@permission_classes([AllowAny])
def reader_login(request):
    from apps.account.membership import ReaderProfile
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    try:
        reader = ReaderProfile.objects.get(username=username, is_active=True)
    except ReaderProfile.DoesNotExist:
        return Response({"error": "用户不存在"}, status=404)
    if not _verify_password(password, reader.password_hash):
        return Response({"error": "密码错误"}, status=401)
    token = _generate_token(reader.id)
    return Response({"token": token, "reader_id": reader.id, "username": reader.username,
                     "is_vip": reader.is_vip, "membership_level": reader.membership_level})

@api_view(["POST"])
@permission_classes([AllowAny])
def reader_register(request):
    from apps.account.membership import ReaderProfile
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    if not username or not password:
        return Response({"error": "用户名和密码必填"}, status=400)
    if ReaderProfile.objects.filter(username=username).exists():
        return Response({"error": "用户名已存在"}, status=400)
    reader = ReaderProfile.objects.create(
        username=username, password_hash=_hash_password(password),
        email=request.data.get("email", ""), nickname=request.data.get("nickname", username),
    )
    token = _generate_token(reader.id)
    return Response({"token": token, "reader_id": reader.id, "username": reader.username}, status=201)
