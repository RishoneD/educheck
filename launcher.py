import os
import sys
import threading
import time
import webview
from updater import check_and_update, EXE_DIR


def _get_app_path():
    """מחפש app.py ליד ה-EXE קודם (עדכון), ואחרכך בתוך החבילה."""
    external = os.path.join(EXE_DIR, 'app.py')
    if os.path.exists(external):
        return external
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'app.py')
    return external


def _start_streamlit(app_path):
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)  # data/ יחסי עובד

    # bootstrap.run קורא ל-signal.signal שנכשל בthread שאינו ראשי
    import signal
    _orig_signal = signal.signal
    def _safe_signal(sig, handler):
        try:
            return _orig_signal(sig, handler)
        except ValueError:
            pass
    signal.signal = _safe_signal

    from streamlit.web import bootstrap
    bootstrap.run(
        app_path, '', [],
        flag_options={
            'server.headless': True,
            'server.port': 8501,
            'server.address': 'localhost',
            'global.developmentMode': False,
        }
    )

    signal.signal = _orig_signal


def _wait_for_streamlit(timeout=30):
    import urllib.request
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen('http://localhost:8501', timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    check_and_update()

    app_path = _get_app_path()
    threading.Thread(target=_start_streamlit, args=(app_path,), daemon=True).start()

    if not _wait_for_streamlit():
        webview.create_window(
            'Gradify — שגיאה',
            html='<h3 style="font-family:Arial;direction:rtl;'
                 'text-align:center;margin-top:40px">'
                 'לא ניתן להפעיל את האפליקציה. נסה שוב.</h3>',
        )
        webview.start()
        return

    webview.create_window(
        title='Gradify — בודק ציונים',
        url='http://localhost:8501',
        width=1200,
        height=800,
        resizable=True,
        min_size=(900, 600),
    )
    webview.start()


if __name__ == '__main__':
    main()
