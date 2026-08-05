import json
import os
import sys
import urllib.request

GITHUB_API = "https://api.github.com/repos/RishoneD/educheck/releases/latest"

EXE_DIR = (os.path.dirname(sys.executable)
           if getattr(sys, 'frozen', False)
           else os.path.dirname(os.path.abspath(__file__)))

VERSION_FILE = os.path.join(EXE_DIR, 'version.txt')


def _parse_ver(v):
    return tuple(int(x) for x in v.split('.'))


def get_current_version():
    try:
        with open(VERSION_FILE) as f:
            return f.read().strip()
    except Exception:
        return '0.0.0'


def check_update():
    """בודק אם קיימת גרסה חדשה. אם כן, מגדיר env vars לapp.py."""
    try:
        req = urllib.request.Request(
            GITHUB_API, headers={'User-Agent': 'Gradify'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        latest = data['tag_name'].lstrip('v')
        current = get_current_version()

        if _parse_ver(latest) > _parse_ver(current):
            os.environ['GRADIFY_UPDATE'] = latest
            os.environ['GRADIFY_DOWNLOAD_URL'] = data.get('html_url', '')

    except Exception:
        pass
