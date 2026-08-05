"""
שליחת פידבק ל-Telegram.
"""
import sys
import os
import json
import socket
import urllib.request
import urllib.parse
import urllib.error


def _load_config():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base, 'feedback_config.py')
    cfg = {}
    with open(config_path, encoding='utf-8') as f:
        exec(f.read(), cfg)
    return cfg.get('TELEGRAM_TOKEN', ''), cfg.get('TELEGRAM_CHAT_ID', '')


def send_feedback(category: str, teacher: str, text: str,
                  image_path: str | None = None) -> tuple[bool, str]:
    """
    שולח הודעת פידבק ל-Telegram.
    מחזיר (הצלחה, הודעת שגיאה).
    """
    try:
        token, chat_id = _load_config()
        if not token or not chat_id:
            return False, 'הגדרות שליחה חסרות'

        icon = '🔧' if category == 'bug' else '💡'
        lines = [
            f'📋 פידבק Gradify',
            f'────────────────────',
            f'סוג: {icon} {"תקלה" if category == "bug" else "הצעת שיפור"}',
        ]
        if teacher.strip():
            lines.append(f'מורה: {teacher.strip()}')
        lines += ['────────────────────', text.strip()]

        message = '\n'.join(lines)

        if image_path and os.path.exists(image_path):
            _send_photo(token, chat_id, message, image_path)
        else:
            _send_message(token, chat_id, message)

        return True, ''

    except FileNotFoundError:
        return False, 'שגיאה פנימית — פנה למפתח'
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            return False, 'השליחה לקחה יותר מדי זמן — בדוק חיבור לאינטרנט ונסה שוב'
        return False, 'לא ניתן לשלוח — בדוק חיבור לאינטרנט'
    except RuntimeError:
        return False, 'שגיאה בשרת המשוב — נסה שוב מאוחר יותר'
    except Exception:
        return False, 'שגיאה בשליחה — נסה שוב'


def _send_message(token: str, chat_id: str, text: str):
    url  = f'https://api.telegram.org/bot{token}/sendMessage'
    data = json.dumps({'chat_id': chat_id, 'text': text}).encode()
    req  = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read())
    if not result.get('ok'):
        raise RuntimeError(result)


def _send_photo(token: str, chat_id: str, caption: str, image_path: str):
    import mimetypes
    boundary = b'----GradifyBoundary'
    body     = b''

    def field(name, value):
        return (b'--' + boundary + b'\r\n'
                b'Content-Disposition: form-data; name="' + name.encode() + b'"\r\n\r\n'
                + value.encode() + b'\r\n')

    body += field('chat_id', chat_id)
    body += field('caption', caption)

    mime = mimetypes.guess_type(image_path)[0] or 'image/png'
    filename = os.path.basename(image_path).encode()
    with open(image_path, 'rb') as f:
        img_data = f.read()
    body += (b'--' + boundary + b'\r\n'
             b'Content-Disposition: form-data; name="photo"; filename="' + filename + b'"\r\n'
             b'Content-Type: ' + mime.encode() + b'\r\n\r\n'
             + img_data + b'\r\n')
    body += b'--' + boundary + b'--\r\n'

    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    req = urllib.request.Request(
        url, data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    if not result.get('ok'):
        raise RuntimeError(result)
