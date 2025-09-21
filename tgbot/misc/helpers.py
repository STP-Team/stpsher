import random
import string

from tgbot.misc.dicts import roles


def generate_auth_code(length=6):
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(random.choice(chars) for _ in range(length))


def get_role(role_id: int = None, role_name: str = None):
    if role_id is not None:
        return roles.get(role_id)
    elif role_name is not None:
        for r_id, data in roles.items():
            if data["name"] == role_name:
                return {r_id: data}
    return None
