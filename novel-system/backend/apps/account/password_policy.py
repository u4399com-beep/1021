"""Password strength policy (v107) — enforce minimum complexity."""
import re

MIN_LENGTH = 12
REQUIRE_UPPER = True
REQUIRE_LOWER = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < MIN_LENGTH:
        return False, f"密码至少 {MIN_LENGTH} 字符"
    if REQUIRE_UPPER and not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"
    if REQUIRE_LOWER and not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"
    if REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, "密码必须包含数字"
    if REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "密码必须包含特殊字符"
    return True, "密码强度合格"
