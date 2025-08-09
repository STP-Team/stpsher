import random
import string


def generate_auth_code(length=6):
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(random.choice(chars) for _ in range(length))
