#!/usr/bin/env python3
"""Small checks for Textpress helpers and a withdrawn Tk smoke."""
from __future__ import annotations

from pathlib import Path

from core import (
    APP_NAME,
    CONF_PATH,
    decode_bytes,
    detect_lang,
    encode_for_save,
    replace_all_text,
    search_text,
    spans,
    toggle_comment,
)


def test_detect_lang():
    assert detect_lang("a.py") == "python"
    assert detect_lang("B.TS") == "typescript"
    assert detect_lang("x.md") == "markdown"
    assert detect_lang("noext") == "text"


def test_app_identity():
    assert APP_NAME == "Textpress"
    assert CONF_PATH.name == ".textpress.json"


def test_decode_eol_and_cp949():
    text, enc, eol = decode_bytes(b"hello\r\nworld")
    assert text == "hello\nworld" and eol == "\r\n" and enc == "utf-8"
    text, enc, eol = decode_bytes("한글".encode("cp949"))
    assert text == "한글" and enc == "cp949"
    assert encode_for_save("a\nb", "utf-8", "\r\n") == b"a\r\nb"
    try:
        decode_bytes(b"a\0b")
        raise AssertionError("binary")
    except ValueError:
        pass


def test_comment_and_search():
    assert toggle_comment(["def x():"], "# ") == ["# def x():"]
    assert toggle_comment(["# def x():"], "# ") == ["def x():"]
    m, _ = search_text("abc def abc", "abc", False, True, 1)
    assert m.span() == (8, 11)
    assert replace_all_text("abc def abc", "abc", "X", False, True) == ("X def X", 2)


def test_spans_python_js_html():
    kinds = {k for k, _, _ in spans('def foo():\n    # hi\n    return "a"\n', "python")}
    assert {"keyword", "comment", "string", "func"} <= kinds
    kinds = {k for k, _, _ in spans('const x = "a"; // c\nfunction f(){}', "javascript")}
    assert "keyword" in kinds and "string" in kinds
    kinds = {k for k, _, _ in spans('<div class="a"><!--c--></div>', "html")}
    assert "keyword" in kinds and "comment" in kinds


def test_gui_smoke():
    from texter import App

    app = App()
    app.root.withdraw()
    ed = app._ed()
    assert ed is not None
    ed.text.delete("1.0", "end")
    ed.text.insert("1.0", 'def foo():\n    return "hi"\n')
    ed.lang = "python"
    ed.highlight()
    assert "keyword" in ed.text.tag_names("1.0")
    assert ed.mark_all("foo", False, True) >= 1
    ed.text.mark_set("insert", "1.0")
    ed.toggle_line_comment()
    assert ed.content().lstrip().startswith("#")
    app.new_tab()
    assert len(app.editors) >= 2
    app.close_tab(force=True)
    app.show_settings()
    assert app._prefs.winfo_exists()
    app._prefs.destroy()
    app.root.destroy()


if __name__ == "__main__":
    test_detect_lang()
    test_app_identity()
    test_decode_eol_and_cp949()
    test_comment_and_search()
    test_spans_python_js_html()
    test_gui_smoke()
    print("ok")
