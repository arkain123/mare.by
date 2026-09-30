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


def get_storage_stats():
    """Get statistics about uploaded files"""
    if not os.path.isdir(UPLOAD_FOLDER):
        return {"files_count": 0, "total_size": 0, "total_size_formatted": "0 B"}
    
    files_count = 0
    total_size = 0
    
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                files_count += 1
                total_size += os.path.getsize(filepath)
    except OSError:
        pass
    
    return {
        "files_count": files_count,
        "total_size": total_size,
        "total_size_formatted": format_size(total_size)
    }


def format_size(bytes_size):
    """Format bytes to human readable format"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / 1024 / 1024 / 1024:.2f} GB"
    if bytes_size >= 1024 * 1024:
        return f"{bytes_size / 1024 / 1024:.1f} MB"
    if bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} KB"
    return f"{bytes_size} B"
