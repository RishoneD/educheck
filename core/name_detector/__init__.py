import os
import sys
import streamlit.components.v1 as components

if getattr(sys, 'frozen', False):
    _DIR = os.path.join(sys._MEIPASS, 'core', 'name_detector')
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

_detect = components.declare_component('gradify_name_detector', path=_DIR)


def detect_name_rects(names: list[str]) -> list | None:
    """
    מחזיר list של [x1,y1,x2,y2] עבור כל מופע שם תלמיד בדף.
    מחזיר None לפני שה-JS מסיים.
    """
    return _detect(names=names, default=None)
