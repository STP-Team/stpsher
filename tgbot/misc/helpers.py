import random
import string

import pytz

from tgbot.misc.dicts import roles

tz = pytz.timezone("Asia/Yekaterinburg")


def generate_auth_code(length=6):
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(random.choice(chars) for _ in range(length))


def get_role(role_id: int = None, role_name: str = None, return_id: bool = False):
    if role_id is not None:
        return role_id if return_id else roles.get(role_id)

    if role_name is not None:
        for r_id, data in roles.items():
            if data["name"] == role_name:
                return r_id if return_id else data

    return None
