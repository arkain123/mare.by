import os
import random
import string

from config import BANNED_EXTENSIONS, UPLOAD_FOLDER


def is_allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext not in BANNED_EXTENSIONS


def generate_short_id(length=8):
    chars = string.ascii_lowercase + string.digits + string.ascii_uppercase
    existing = os.listdir(UPLOAD_FOLDER) if os.path.isdir(UPLOAD_FOLDER) else []

    while True:
        short_id = ''.join(random.choice(chars) for _ in range(length))
        if not any(f.startswith(short_id) for f in existing):
            return short_id


def delete_uploaded_file(filename):
    if not filename or filename != os.path.basename(filename) or filename in (".", ".."):
        return False, "Incorrect filename"

    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.isfile(path):
        return False, "File not found"

    try:
        os.remove(path)
        return True, "File deleted"
    except OSError as e:
        return False, f"Deleting error: {e}"
