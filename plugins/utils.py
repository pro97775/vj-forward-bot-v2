# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import time as tm
import base64
import struct
from pyrogram.file_id import FileId
from database import db
from .test import parse_buttons

STATUS = {}


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def unpack_new_file_id(new_file_id: str) -> str:
    """Return a canonical bot-independent unpacked file_id for deduplication."""
    if not new_file_id:
        return ""
    try:
        decoded = FileId.decode(new_file_id)
        return encode_file_id(
            struct.pack(
                "<iiqq",
                int(decoded.file_type),
                decoded.dc_id,
                decoded.media_id,
                decoded.access_hash,
            )
        )
    except Exception:
        return str(new_file_id)


def get_media_object(msg):
    """Extract media object from any supported Pyrogram message media type."""
    if not getattr(msg, "media", None):
        return None
    for attr in ("document", "video", "audio", "photo", "animation", "voice", "sticker"):
        media_obj = getattr(msg, attr, None)
        if media_obj is not None:
            return media_obj
    media_val = getattr(msg.media, "value", None)
    if media_val:
        return getattr(msg, media_val, None)
    return None


def extract_media_file_id(msg) -> str:
    """Return the unpacked canonical file_id for any media message (or empty string)."""
    media_obj = get_media_object(msg)
    if media_obj and getattr(media_obj, "file_id", None):
        return unpack_new_file_id(media_obj.file_id)
    return ""


def get_media_meta(msg):
    """Return (file_name, file_size_bytes, raw_file_id) for any media message."""
    media_obj = get_media_object(msg)
    if not media_obj:
        return "", 0, None
    file_name = getattr(media_obj, "file_name", "") or ""
    file_size = getattr(media_obj, "file_size", 0) or 0
    raw_file_id = getattr(media_obj, "file_id", None)
    return file_name, file_size, raw_file_id


def get_size(size) -> str:
    if not size:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def clean_text(text: str, cleaners: dict = None, replacements: dict = None) -> str:
    """
    1-Click Auto-Cleaners & Custom Word Replacer/Remover:
      - html_links: strip <a href="...">...</a> tags
      - tme: strip t.me / telegram.me / telegram.dog links
      - url: strip http(s):// and www. web links
      - username: strip @usernames
      - replacements: replace/remove custom words
    """
    if not text:
        return ""
    cleaners = cleaners or {}
    replacements = replacements or {}
    result = text

    # 1. Strip HTML anchor tags
    if cleaners.get("html_links"):
        result = re.sub(r"<a\b[^>]*>.*?</a>", "", result, flags=re.IGNORECASE | re.DOTALL)
        result = re.sub(r"</?a\b[^>]*>", "", result, flags=re.IGNORECASE)

    # 2. Strip t.me / telegram links
    if cleaners.get("tme"):
        result = re.sub(
            r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/[A-Za-z0-9_+/?=&-]+",
            "",
            result,
            flags=re.IGNORECASE,
        )

    # 3. Strip general web URLs
    if cleaners.get("url"):
        result = re.sub(
            r"(?:https?://|www\.)[^\s<>\"]+",
            "",
            result,
            flags=re.IGNORECASE,
        )

    # 4. Strip @usernames
    if cleaners.get("username"):
        result = re.sub(r"@[A-Za-z0-9_]{3,}", "", result)

    # 5. Custom Word Replacer & Remover
    if replacements and isinstance(replacements, dict):
        for old_word, new_word in replacements.items():
            if old_word:
                result = re.sub(
                    re.escape(str(old_word)),
                    str(new_word or ""),
                    result,
                    flags=re.IGNORECASE,
                )

    # 6. Tidy extra spaces & blank lines while preserving intentional line breaks
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"\n[ \t]+", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def apply_prefix_suffix(text: str, prefix: str = None, suffix: str = None) -> str:
    parts = []
    if prefix and str(prefix).strip():
        parts.append(str(prefix).strip())
    if text and str(text).strip():
        parts.append(str(text).strip())
    if suffix and str(suffix).strip():
        parts.append(str(suffix).strip())
    return "\n\n".join(parts)


def build_smart_caption(msg, configs: dict) -> str:
    """
    Smart Caption Engine:
      - Applies 1-Click Auto-Cleaners & Word Replacer to original caption and filename
      - Substitutes {filename}, {size}, and {caption} placeholders safely
      - Prepends Prefix and appends Suffix blocks
    """
    cleaners = configs.get("cleaners") or {}
    replacements = configs.get("replacements") or {}
    prefix = configs.get("prefix")
    suffix = configs.get("suffix")
    template = configs.get("caption")

    if getattr(msg, "media", None):
        file_name, file_size, _ = get_media_meta(msg)
        cleaned_fname = clean_text(file_name, cleaners, replacements) if file_name else ""
        size_str = get_size(file_size) if file_size else ""
        raw_caption = msg.caption.html if getattr(msg, "caption", None) else ""
        cleaned_caption = clean_text(raw_caption, cleaners, replacements)

        if template:
            body = str(template)
            body = body.replace("{filename}", cleaned_fname)
            body = body.replace("{size}", size_str)
            body = body.replace("{caption}", cleaned_caption)
            body = clean_text(body, {}, {})
        else:
            body = cleaned_caption

        return apply_prefix_suffix(body, prefix, suffix)

    # Plain text message handling
    raw_text = msg.text.html if getattr(msg, "text", None) else ""
    cleaned_text = clean_text(raw_text, cleaners, replacements)
    return apply_prefix_suffix(cleaned_text, prefix, suffix)


class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS

    def verify(self):
        return self.data.get(self.id)

    def store(self, From, to, skip, limit, mode=None):
        self.data[self.id] = {
            "id": self.id,
            "FROM": From,
            "TO": to,
            "total_files": 0,
            "skip": int(skip),
            "limit": int(limit),
            "fetched": int(skip),
            "filtered": 0,
            "deleted": 0,
            "duplicate": 0,
            "total": int(limit),
            "start": 0,
            "mode": mode,
        }
        self.get(full=True)
        return STS(self.id)

    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if not values:
            return None
        if not full:
            return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def add(self, key=None, value=1, time=False, start_time=None):
        if self.id not in self.data:
            return
        if time:
            return self.data[self.id].update(
                {"start": tm.time() if start_time is None else start_time}
            )
        self.data[self.id].update({key: self.get(key) + value})

    def set_val(self, key, value):
        if self.id in self.data:
            self.data[self.id][key] = value

    def divide(self, no, by):
        by = 1 if int(by) == 0 else by
        return int(no) / by

    async def get_data(self, user_id):
        bots = await db.get_bots(user_id)
        userbot = await db.get_userbot(user_id)
        filters = await db.get_filters(user_id)
        configs = await db.get_configs(user_id)

        forward_mode = configs.get("forward_mode", "pool")
        if forward_mode == "userbot" and userbot:
            primary_bot = userbot
        elif bots:
            primary_bot = bots[0]
        else:
            primary_bot = userbot

        duplicate = bool(configs.get("duplicate", True))
        min_s = configs.get("min_size", 0) or 0
        max_s = configs.get("max_size", 0) or 0
        button = parse_buttons(configs["button"] if configs.get("button") else "")

        datas = {
            "filters": filters,
            "keywords": configs.get("keywords"),
            "min_size": min_s,
            "max_size": max_s,
            "extensions": configs.get("extension"),
            "skip_duplicate": duplicate,
            "db_uri": configs.get("db_uri"),
            "prefix": configs.get("prefix"),
            "suffix": configs.get("suffix"),
            "cleaners": configs.get("cleaners") or {},
            "replacements": configs.get("replacements") or {},
            "forward_mode": forward_mode,
            "bots": bots,
            "userbot": userbot,
            "raw_configs": configs,
        }
        return (
            primary_bot,
            configs.get("caption"),
            configs.get("forward_tag", False),
            datas,
            configs.get("protect", False),
            button,
        )