import json
import threading
from datetime import datetime

import requests

from config import (
    BLOCKED_IP_FILE,
    ESCALATED_IP_FILE,
    TG_ADMIN_IDS,
    TG_BOT_TOKEN,
    TG_CHAT_ID,
)
from file_utils import delete_uploaded_file
from ip_utils import append_ip_to_file, read_ip_file, remove_ip_from_file
from ip_lookup import format_ip_origin

# ---------- Low-level Telegram API ----------
def tg_api(method, data=None):
    if not TG_BOT_TOKEN:
        print("[TG] TELEGRAM_BOT_TOKEN is not set")
        return None
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    try:
        r = requests.post(url, data=data or {}, timeout=10)
        if r.status_code != 200:
            print(f"[TG] {method} error: {r.status_code} {r.text}")
        return r
    except requests.RequestException as e:
        print(f"[TG] {method} exception: {e}")
        return None


def tg_send_message(chat_id, text, reply_markup=None, parse_mode=None):
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return tg_api("sendMessage", data)


def tg_answer_callback(callback_id, text=None, show_alert=False):
    data = {"callback_query_id": callback_id}
    if text:
        data["text"] = text
    if show_alert:
        data["show_alert"] = "true"
    return tg_api("answerCallbackQuery", data)


def tg_edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return tg_api("editMessageText", data)


def is_admin(user_id):
    return str(user_id) in TG_ADMIN_IDS


def escape_markdown(text):
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '!']
    for ch in special_chars:
        text = text.replace(ch, '\\' + ch)
    return text

def build_notification_markup(filename, user_ip, escalated):
    row = [
        {"text": "Remove file", "callback_data": f"del:{filename}"},
    ]
    if escalated:
        row.append({"text": "Deescalate", "callback_data": f"desc:{user_ip}"})
    else:
        row.append({"text": "Escalate", "callback_data": f"esc:{user_ip}"})
    return {"inline_keyboard": [row]}

def send_telegram_notification(filename, original_filename, file_size, file_url,
                               user_ip, escalated=False, source='web'):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("[TG] Notification skipped: missing token or chat_id")
        return

    def _send():
        filename_esc = escape_markdown(filename)
        original_filename_esc = escape_markdown(original_filename)
        user_ip_esc = escape_markdown(user_ip)
        file_url_esc = escape_markdown(file_url)

        ip_origin = format_ip_origin(user_ip)
        origin_line = f"\n🔹 *IP origin:* `{ip_origin}`" if ip_origin else ""

        message = (
            f"📁 *New file uploaded*\n"
            f"🔹 *Source:* {source.upper()}\n"
            f"🔹 *ID:* `{filename_esc}`\n"
            f"🔹 *Original:* {original_filename_esc}\n"
            f"🔹 *Size:* {file_size / 1024:.2f} KB\n"
            f"🔹 *User IP:* `{user_ip_esc}`"
            f"{origin_line}\n"
            f"🔹 *URL:* {file_url_esc}\n"
            f"🕒 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if escalated:
            message += (
                "\n\n⚠ *ВНИМАНИЕ!* Файл загружен с плохого IP-адреса!\n"
                "Проверьте содержимое с особой внимательностью!\n"
                "@styrbo @voidoffear"
            )

        reply_markup = build_notification_markup(filename, user_ip, escalated)

        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        try:
            print(f"[TG] Sending notification: {message[:120]}...")
            response = requests.post(url, data={
                "chat_id": TG_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup, ensure_ascii=False),
            }, timeout=5)
            if response.status_code != 200:
                print(f"[TG] send error: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            print(f"[TG] send error: {e}")

    threading.Thread(target=_send, daemon=True).start()

HELP_TEXT = (
    "*Commands:*\n"
    "/escalate `<IP/CIDR>` \\[comment\\] - add to escalated\n"
    "/deescalate `<IP/CIDR>` — remove from escalated\n"
    "/ban `<IP/CIDR>` \\[comment\\] - add to banned\n"
    "/unban `<IP/CIDR>` - remove from banned\n"
    "/list\\_escalated - show escalated\n"
    "/list\\_banned - show banned\n"
    "/delete `<filename>` - delete uploaded file\n"
)


def handle_telegram_message(message):
    text = (message.get("text") or "").strip()
    if not text.startswith("/"):
        return

    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")

    if not is_admin(user_id):
        tg_send_message(chat_id, "Unsufficient rights.")
        return

    parts = text.split()
    cmd = parts[0].split("@", 1)[0].lower()
    args = parts[1:]

    if cmd in ("/start", "/help"):
        tg_send_message(chat_id, HELP_TEXT, parse_mode="Markdown")

    elif cmd == "/escalate":
        if not args:
            tg_send_message(chat_id, "Usage: /escalate <IP/CIDR> [comment]")
            return
        _, msg = append_ip_to_file(ESCALATED_IP_FILE, args[0], " ".join(args[1:]))
        tg_send_message(chat_id, msg)

    elif cmd == "/deescalate":
        if not args:
            tg_send_message(chat_id, "Usage: /deescalate <IP/CIDR>")
            return
        _, msg = remove_ip_from_file(ESCALATED_IP_FILE, args[0])
        tg_send_message(chat_id, msg)

    elif cmd == "/ban":
        if not args:
            tg_send_message(chat_id, "Usage: /ban <IP/CIDR> [comment]")
            return
        _, msg = append_ip_to_file(BLOCKED_IP_FILE, args[0], " ".join(args[1:]))
        tg_send_message(chat_id, msg)

    elif cmd == "/unban":
        if not args:
            tg_send_message(chat_id, "Usage: /unban <IP/CIDR>")
            return
        _, msg = remove_ip_from_file(BLOCKED_IP_FILE, args[0])
        tg_send_message(chat_id, msg)

    elif cmd == "/list_escalated":
        tg_send_message(chat_id, "Escalated:\n" + read_ip_file(ESCALATED_IP_FILE))

    elif cmd == "/list_banned":
        tg_send_message(chat_id, "Banned:\n" + read_ip_file(BLOCKED_IP_FILE))

    elif cmd == "/delete":
        if not args:
            tg_send_message(chat_id, "Usage: /delete <filename>")
            return
        _, msg = delete_uploaded_file(args[0])
        tg_send_message(chat_id, msg)

    else:
        tg_send_message(chat_id, "Unknown command. /help")


# ---------- Inline-buttons ----------
def handle_telegram_callback(callback):
    callback_id = callback.get("id")
    user_id = callback.get("from", {}).get("id")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    data = callback.get("data", "")

    if not is_admin(user_id):
        tg_answer_callback(callback_id, "Unsufficient rights", show_alert=True)
        return

    if data.startswith("del:"):
        filename = data[4:]
        ok, msg = delete_uploaded_file(filename)

        if ok:
            old_text = message.get("text", "")
            new_text = old_text + f"\n\nRemoved: {filename}"
            tg_edit_message_text(
                chat_id,
                message_id,
                new_text,
                reply_markup={"inline_keyboard": []},
                parse_mode="Markdown",
            )
            tg_answer_callback(callback_id, "File deleted")
        else:
            tg_answer_callback(callback_id, msg, show_alert=True)
        return

    # --- Escalate / Deescalate ---
    if data.startswith("esc:") or data.startswith("desc:"):
        action = "esc" if data.startswith("esc:") else "desc"
        ip = data.split(":", 1)[1]

        if action == "esc":
            ok, msg = append_ip_to_file(ESCALATED_IP_FILE, ip, f"via button by {user_id}")
        else:
            ok, msg = remove_ip_from_file(ESCALATED_IP_FILE, ip)

        tg_answer_callback(callback_id, msg, show_alert=True)

        if not ok:
            return

        new_escalated = (action == "esc")
        old_text = message.get("text", "")
        old_markup = message.get("reply_markup", {}) or {}
        rows = old_markup.get("inline_keyboard", [])

        new_rows = []
        for row in rows:
            new_row = []
            for btn in row:
                btn_data = btn.get("callback_data", "")
                if btn_data.startswith("esc:") or btn_data.startswith("desc:"):
                    if new_escalated:
                        new_row.append({"text": "Deescalate", "callback_data": f"desc:{ip}"})
                    else:
                        new_row.append({"text": "Escalate", "callback_data": f"esc:{ip}"})
                else:
                    new_row.append(btn)
            new_rows.append(new_row)

        tg_edit_message_text(
            chat_id,
            message_id,
            old_text,
            reply_markup={"inline_keyboard": new_rows},
            parse_mode="Markdown",
        )
        return

    tg_answer_callback(callback_id, "Unknown action", show_alert=True)
