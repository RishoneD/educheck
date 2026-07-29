import json
import os
import sys
import urllib.request
import zipfile
import tkinter as tk
from tkinter import messagebox

GITHUB_API = "https://api.github.com/repos/RishoneD/educheck/releases/latest"
_ALLOWED_EXTS = {'.py', '.xlsx', '.txt'}

# תיקיית הבסיס: ליד ה-EXE כשקפוא, ליד __file__ בפיתוח
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


def _show_status(msg):
    win = tk.Tk()
    win.title('Gradify')
    win.geometry('320x90')
    win.resizable(False, False)
    win.attributes('-topmost', True)
    win.configure(bg='white')
    tk.Label(win, text=msg, font=('Arial', 11), bg='white', pady=25).pack()
    win.update()
    return win


def check_and_update():
    try:
        req = urllib.request.Request(
            GITHUB_API, headers={'User-Agent': 'Gradify'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        latest  = data['tag_name'].lstrip('v')
        current = get_current_version()

        if _parse_ver(latest) <= _parse_ver(current):
            return

        win = _show_status(f'מוריד עדכון גרסה {latest}...')

        zip_path = os.path.join(EXE_DIR, 'update.zip')
        with urllib.request.urlopen(data['zipball_url'], timeout=60) as r:
            with open(zip_path, 'wb') as f:
                f.write(r.read())

        base = os.path.realpath(EXE_DIR)
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            # GitHub zipball: תיקייה עליונה כמו "RishoneD-educheck-abc123/"
            prefix = names[0].split('/')[0] + '/' if names else ''
            for name in names:
                if not name.startswith(prefix):
                    continue
                rel = name[len(prefix):]
                if not rel:
                    continue
                ext = os.path.splitext(rel)[1].lower()
                if ext not in _ALLOWED_EXTS:
                    continue
                dest = os.path.realpath(os.path.join(base, rel))
                if not dest.startswith(base + os.sep):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(name) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())

        os.remove(zip_path)

        with open(VERSION_FILE, 'w') as f:
            f.write(latest)

        win.destroy()

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo(
            'Gradify — עדכון',
            f'עדכון הותקן בהצלחה!\nגרסה {latest}',
            parent=root,
        )
        root.destroy()

    except Exception:
        pass
