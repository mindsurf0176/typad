#!/usr/bin/env python3
"""Textpress — Notepad++-style editor. Stdlib only."""
from __future__ import annotations

import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from core import (
    APP_NAME,
    COMMENT,
    MAX_HIGHLIGHT,
    MAX_OPEN_WARN,
    decode_bytes,
    detect_lang,
    encode_for_save,
    find_in_files,
    load_conf,
    replace_all_text,
    save_conf,
    search_text,
    skip_dir,
    spans,
    toggle_comment,
)

MOD = "Command" if sys.platform == "darwin" else "Control"

THEMES = {
    "dark": {
        "bg": "#171615", "fg": "#e8e2d6", "muted": "#8a8378", "sel": "#3a342c",
        "caret": "#f3ead8", "gutter_bg": "#171615", "gutter_fg": "#6a645a",
        "current": "#211f1c", "status_bg": "#1e1c1a", "status_fg": "#9a9388",
        "bar": "#1e1c1a", "tab": "#1e1c1a", "sidebar": "#1b1917",
        "border": "#2c2926", "find": "#4a3a22", "match": "#3a4630",
        "keyword": "#c4a574", "string": "#c17a5a", "comment": "#7a7568",
        "number": "#b8a88a", "func": "#d8cbb0", "type": "#8fa38a",
        "bookmark": "#3a3548", "btn": "#2a2724", "field": "#121110",
    },
    "light": {
        "bg": "#f7f4ee", "fg": "#2a2723", "muted": "#7a7468", "sel": "#e4d9c5",
        "caret": "#1a1816", "gutter_bg": "#f7f4ee", "gutter_fg": "#9a9388",
        "current": "#efeae0", "status_bg": "#efeae3", "status_fg": "#6d675c",
        "bar": "#efeae3", "tab": "#efeae3", "sidebar": "#f1ece4",
        "border": "#ddd6c8", "find": "#ead8a8", "match": "#d5e0b8",
        "keyword": "#8a5a32", "string": "#9c3d2e", "comment": "#7a7568",
        "number": "#6b5a3a", "func": "#3f3a34", "type": "#4d6a4a",
        "bookmark": "#ddd4f0", "btn": "#e6dfd4", "field": "#fffdf8",
    },
}


class Editor(tk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master, bg=app.t["bg"])
        self.app = app
        self.path: Path | None = None
        self.encoding = "utf-8"
        self.eol = "\n"
        self.lang = "text"
        self.saved = ""
        self._hl = None
        self.gutter = tk.Text(
            self, width=5, padx=6, takefocus=0, wrap="none", bd=0,
            highlightthickness=0, state="disabled", cursor="arrow",
        )
        self.text = tk.Text(
            self, wrap="none", undo=True, maxundo=-1, autoseparators=True,
            bd=0, highlightthickness=0, padx=14, pady=10, insertwidth=2,
            spacing1=2, spacing3=2,
        )
        self.rule = tk.Frame(self, width=1, bd=0, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical")
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(xscrollcommand=self._xscroll)

        def yscroll(*a):
            self.sb.set(*a)
            self.gutter.yview_moveto(a[0])
            self._show_bar(self.sb, a)

        self.text.configure(yscrollcommand=yscroll)
        self.sb.configure(command=self._scroll_both)
        self.gutter.grid(row=0, column=0, sticky="nsw")
        self.rule.grid(row=0, column=1, sticky="ns")
        self.text.grid(row=0, column=2, sticky="nsew")
        self.sb.grid(row=0, column=3, sticky="ns")
        self.hsb.grid(row=1, column=2, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.text.bind("<<Modified>>", self._modified)
        self.text.bind("<KeyRelease>", self._cursor)
        self.text.bind("<ButtonRelease-1>", self._cursor)
        self.text.bind("<Configure>", lambda e: self.redraw_gutter())
        self.text.bind("<MouseWheel>", lambda e: self.after_idle(self.redraw_gutter))
        self.text.bind("<Return>", self._autoindent)
        self.text.bind("<Tab>", self._tab)
        self.text.bind("<ISO_Left_Tab>", self._dedent)
        self.text.bind("<Shift-Tab>", self._dedent)
        self.apply_theme()

    def _scroll_both(self, *a):
        self.text.yview(*a)
        self.gutter.yview(*a)

    def _xscroll(self, *a):
        self.hsb.set(*a)
        self._show_bar(self.hsb, a, grid={"row": 1, "column": 2, "sticky": "ew"})

    def _show_bar(self, bar, a, grid=None):
        try:
            lo, hi = float(a[0]), float(a[1])
        except (TypeError, ValueError):
            return
        if lo <= 0.0 and hi >= 1.0:
            bar.grid_remove()
        elif grid:
            bar.grid(**grid)
        else:
            bar.grid()

    def apply_theme(self):
        t = self.app.t
        font = self.app.font
        self.configure(bg=t["bg"])
        self.rule.configure(bg=t["border"])
        self.gutter.configure(
            bg=t["gutter_bg"], fg=t["gutter_fg"], font=self.app.gutter_font,
            insertbackground=t["gutter_bg"], padx=10, pady=10, spacing1=2, spacing3=2,
        )
        self.text.configure(
            bg=t["bg"], fg=t["fg"], font=font, insertbackground=t["caret"],
            selectbackground=t["sel"], selectforeground=t["fg"],
            inactiveselectbackground=t["sel"],
            tabs=(font.measure(" " * self.app.tab_width),),
            wrap="word" if self.app.wrap else "none",
        )
        for name in ("keyword", "string", "comment", "number", "func", "type"):
            self.text.tag_configure(name, foreground=t[name])
        self.text.tag_configure("current", background=t["current"])
        self.text.tag_configure("find", background=t["find"])
        self.text.tag_configure("match", background=t["match"])
        self.text.tag_configure("bookmark", background=t["bookmark"])
        self.text.tag_lower("current")
        if self.app.show_gutter:
            self.gutter.grid()
            self.rule.grid()
        else:
            self.gutter.grid_remove()
            self.rule.grid_remove()
        self.redraw_gutter()
        self.highlight()

    def content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def dirty(self) -> bool:
        return self.content() != self.saved

    def title(self) -> str:
        name = self.path.name if self.path else "제목 없음"
        return ("● " if self.dirty() else "") + name

    def _modified(self, _=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self.app.refresh_tab(self)
            self.schedule_hl()
            self.redraw_gutter()
            self.app.status()

    def _cursor(self, _=None):
        self.mark_current()
        self.match_brace()
        self.app.status()

    def mark_current(self):
        self.text.tag_remove("current", "1.0", "end")
        self.text.tag_add("current", "insert linestart", "insert lineend+1c")
        self.text.tag_lower("current")

    def match_brace(self):
        self.text.tag_remove("match", "1.0", "end")
        pairs = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
        ch = self.text.get("insert")
        at = "insert"
        if ch not in pairs:
            ch = self.text.get("insert-1c")
            at = "insert-1c"
            if ch not in pairs:
                return
        src = self.content()
        start = len(self.text.get("1.0", at))
        target = pairs[ch]
        step = 1 if ch in "([{" else -1
        depth = 0
        i = start
        n = len(src)
        # ponytail: linear scan; virtualize if files routinely exceed a few MB
        while 0 <= i < n and abs(i - start) < 80_000:
            c = src[i]
            if c == ch:
                depth += 1
            elif c == target:
                depth -= 1
                if depth == 0:
                    self.text.tag_add("match", at, f"{at}+1c")
                    self.text.tag_add("match", f"1.0+{i}c", f"1.0+{i + 1}c")
                    return
            i += step

    def schedule_hl(self):
        if self._hl:
            self.after_cancel(self._hl)
        self._hl = self.after(70, self.highlight)

    def highlight(self):
        self._hl = None
        src = self.content()
        for tag in ("keyword", "string", "comment", "number", "func", "type"):
            self.text.tag_remove(tag, "1.0", "end")
        if not self.app.syntax or self.lang == "text" or len(src) > MAX_HIGHLIGHT:
            return
        for kind, a, b in spans(src, self.lang):
            self.text.tag_add(kind, f"1.0+{a}c", f"1.0+{b}c")

    def redraw_gutter(self):
        last = int(self.text.index("end-1c").split(".")[0])
        marks = set()
        rng = self.text.tag_ranges("bookmark")
        for i in range(0, len(rng), 2):
            marks.add(int(str(rng[i]).split(".")[0]))
        w = max(3, len(str(last)))
        rows = []
        for n in range(1, last + 1):
            num = f"{n:>{w}}"
            rows.append(("· " + num) if n in marks else ("  " + num))
        lines = "\n".join(rows)
        self.gutter.configure(state="normal", width=w + 3)
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", lines)
        self.gutter.configure(state="disabled")
        try:
            self.gutter.yview_moveto(self.text.yview()[0])
        except tk.TclError:
            pass

    def _autoindent(self, _=None):
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r"[ \t]*", line).group(0)
        if line.rstrip().endswith((":", "{", "[", "(")):
            indent += self._pad()
        self.text.insert("insert", "\n" + indent)
        return "break"

    def _tab(self, _=None):
        pad = self._pad()
        try:
            start, end = self.text.index("sel.first"), self.text.index("sel.last")
        except tk.TclError:
            self.text.insert("insert", pad)
            return "break"
        first = int(start.split(".")[0])
        last = int(end.split(".")[0]) - (1 if end.endswith(".0") else 0)
        for n in range(first, last + 1):
            self.text.insert(f"{n}.0", pad)
        return "break"

    def _dedent(self, _=None):
        pad = self._pad()
        nsp = len(pad)
        try:
            start, end = self.text.index("sel.first"), self.text.index("sel.last")
            first = int(start.split(".")[0])
            last = int(end.split(".")[0]) - (1 if end.endswith(".0") else 0)
        except tk.TclError:
            first = last = int(self.text.index("insert").split(".")[0])
        for n in range(first, last + 1):
            line = self.text.get(f"{n}.0", f"{n}.{nsp}")
            if line.startswith(pad):
                cut = nsp
            elif line.startswith("\t"):
                cut = 1
            elif line.startswith(" "):
                cut = min(nsp, len(line) - len(line.lstrip(" ")))
            else:
                cut = 0
            if cut:
                self.text.delete(f"{n}.0", f"{n}.{cut}")
        return "break"

    def _pad(self) -> str:
        return " " * max(1, int(self.app.tab_width))

    def selected_lines(self) -> tuple[str, str]:
        try:
            start = self.text.index("sel.first linestart")
            end = self.text.index("sel.last lineend")
        except tk.TclError:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
        return start, end

    def toggle_line_comment(self):
        prefix = COMMENT.get(self.lang)
        start, end = self.selected_lines()
        src = self.text.get(start, end)
        if not prefix:
            if self.lang in {"html", "xml", "markdown"}:
                stripped = src.strip()
                if stripped.startswith("<!--") and stripped.endswith("-->"):
                    src = src.replace("<!--", "", 1).replace("-->", "", 1)
                else:
                    src = "<!--" + src + "-->"
                self.text.replace(start, end, src)
            return
        self.text.replace(start, end, "\n".join(toggle_comment(src.split("\n"), prefix)))

    def duplicate_line(self):
        start, end = self.text.index("insert linestart"), self.text.index("insert lineend")
        self.text.insert(end, "\n" + self.text.get(start, end))

    def delete_line(self):
        self.text.delete("insert linestart", "insert lineend+1c")

    def move_line(self, delta: int):
        n = int(self.text.index("insert").split(".")[0])
        col = self.text.index("insert").split(".")[1]
        other = n + delta
        last = int(self.text.index("end-1c").split(".")[0])
        if other < 1 or other > last:
            return
        a = self.text.get(f"{n}.0", f"{n}.end")
        b = self.text.get(f"{other}.0", f"{other}.end")
        self.text.replace(f"{n}.0", f"{n}.end", b)
        self.text.replace(f"{other}.0", f"{other}.end", a)
        self.text.mark_set("insert", f"{other}.{col}")
        self._cursor()

    def change_case(self, upper: bool):
        try:
            s, e = self.text.index("sel.first"), self.text.index("sel.last")
        except tk.TclError:
            return
        src = self.text.get(s, e)
        self.text.replace(s, e, src.upper() if upper else src.lower())

    def trim_trailing(self):
        src = "\n".join(ln.rstrip() for ln in self.content().split("\n"))
        self.text.replace("1.0", "end-1c", src)

    def toggle_bookmark(self):
        line = self.text.index("insert linestart")
        ranges = self.text.tag_ranges("bookmark")
        for i in range(0, len(ranges), 2):
            if self.text.compare(line, ">=", ranges[i]) and self.text.compare(line, "<", ranges[i + 1]):
                self.text.tag_remove("bookmark", f"{line}", f"{line} lineend+1c")
                self.redraw_gutter()
                return
        self.text.tag_add("bookmark", line, f"{line} lineend+1c")
        self.redraw_gutter()

    def next_bookmark(self):
        nxt = self.text.tag_nextrange("bookmark", "insert+1c")
        if not nxt:
            nxt = self.text.tag_nextrange("bookmark", "1.0")
        if nxt:
            self.text.mark_set("insert", nxt[0])
            self.text.see("insert")
            self._cursor()

    def goto(self, line: int):
        self.text.mark_set("insert", f"{max(1, line)}.0")
        self.text.see("insert")
        self._cursor()

    def find_next(self, pat: str, regex: bool, case: bool) -> bool:
        if not pat:
            return False
        try:
            start = len(self.text.get("1.0", "insert"))
            m, _ = search_text(self.content(), pat, regex, case, start)
        except re.error:
            return False
        if not m:
            return False
        if m.start() < start and start:
            # wrapped
            pass
        a, b = m.start(), m.end()
        self.text.mark_set("insert", f"1.0+{b}c")
        self.text.see(f"1.0+{a}c")
        self.mark_all(pat, regex, case)
        self._cursor()
        return True

    def mark_all(self, pat: str, regex: bool, case: bool) -> int:
        self.text.tag_remove("find", "1.0", "end")
        if not pat:
            return 0
        try:
            flags = 0 if case else re.I
            rx = re.compile(pat if regex else re.escape(pat), flags)
        except re.error:
            return 0
        n = 0
        for m in rx.finditer(self.content()):
            self.text.tag_add("find", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
            n += 1
            if n > 5000:
                break
        return n

    def replace_one(self, pat: str, repl: str, regex: bool, case: bool) -> bool:
        ranges = self.text.tag_ranges("find")
        if ranges:
            s, e = str(ranges[0]), str(ranges[1])
            src = self.text.get(s, e)
            if regex:
                try:
                    src = re.sub(pat, repl, src, count=1, flags=0 if case else re.I)
                except re.error:
                    return False
            else:
                src = repl
            self.text.replace(s, e, src)
        return self.find_next(pat, regex, case)

    def replace_all(self, pat: str, repl: str, regex: bool, case: bool) -> int:
        try:
            new, n = replace_all_text(self.content(), pat, repl, regex, case)
        except re.error:
            return 0
        if n:
            self.text.replace("1.0", "end-1c", new)
        return n


class App:
    def __init__(self):
        self.conf = load_conf()
        self.theme = self.conf.get("theme", "dark")
        self.wrap = bool(self.conf.get("wrap", False))
        self.font_size = int(self.conf.get("font_size", 13))
        self.font_family = self.conf.get("font_family")
        self.tab_width = int(self.conf.get("tab_width", 4)) or 4
        self.ui_size = max(9, min(16, int(self.conf.get("ui_size", 11))))
        self.restore_session = self.conf.get("restore_session", True)
        self.show_gutter = self.conf.get("show_gutter", True)
        self.syntax = self.conf.get("syntax", True)
        self.recent: list[str] = list(self.conf.get("recent", []))[:15]
        self.folder = Path(self.conf["folder"]).expanduser() if self.conf.get("folder") else None
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        try:
            self.root.tk.call("tk", "appname", APP_NAME)
        except tk.TclError:
            pass
        self.root.minsize(640, 400)
        self.root.geometry(self.conf.get("geometry", "1100x720"))
        self.t = THEMES[self.theme]
        self._init_fonts()
        self._mac_appear()
        self.editors: list[Editor] = []
        self._style()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self._bind()
        self._mac_hooks()
        if self.folder and self.folder.is_dir():
            self._fill_tree(self.folder)
        if self.restore_session:
            for p in self.conf.get("session", []):
                path = Path(p)
                if path.is_file():
                    self.open_path(path)
        for arg in sys.argv[1:]:
            if arg.startswith("-psn") or arg.startswith("-"):
                continue
            path = Path(arg).expanduser()
            if path.is_dir():
                self.open_folder(path)
            elif path.exists():
                self.open_path(path)
        if not self.editors:
            self.new_tab()

    def _family(self, names, fallback):
        have = set(tkfont.families())
        for name in names:
            if name in have:
                return name
        return fallback

    def _init_fonts(self):
        saved = self.font_family
        mono = saved if saved and saved in set(tkfont.families()) else self._family(("D2Coding", "Maple Mono", "Menlo"), "Courier")
        self.font_family = mono
        ui = self._family(("Pretendard", "Apple SD Gothic Neo"), ".AppleSystemUIFont")
        self.font = tkfont.Font(family=mono, size=self.font_size)
        self.gutter_font = tkfont.Font(family=mono, size=max(10, self.font_size - 1))
        self.ui_font = tkfont.Font(family=ui, size=self.ui_size)
        self.ui_small = tkfont.Font(family=ui, size=max(9, self.ui_size - 1))

    def _mac_appear(self):
        if sys.platform != "darwin":
            return
        look = "darkaqua" if self.theme == "dark" else "aqua"
        try:
            self.root.tk.call("::tk::unsupported::MacWindowStyle", "appearance", self.root, look)
        except tk.TclError:
            pass

    def _style(self):
        t = self.t
        self.root.configure(bg=t["bar"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=t["bar"], foreground=t["fg"], fieldbackground=t["field"], bordercolor=t["border"], darkcolor=t["bar"], lightcolor=t["bar"])
        style.configure("TNotebook", background=t["bar"], borderwidth=0, tabmargins=[8, 6, 8, 0])
        style.configure("TNotebook.Tab", background=t["tab"], foreground=t["muted"], padding=(max(10, self.ui_size), max(5, self.ui_size - 5)), borderwidth=0, focuscolor=t["tab"], font=self.ui_font)
        style.map("TNotebook.Tab",
                  background=[("selected", t["bg"]), ("!selected", t["tab"])],
                  foreground=[("selected", t["fg"]), ("!selected", t["muted"])],
                  lightcolor=[("selected", t["bg"]), ("!selected", t["tab"])],
                  darkcolor=[("selected", t["bg"]), ("!selected", t["tab"])],
                  bordercolor=[("selected", t["bg"]), ("!selected", t["tab"])])
        style.configure("Treeview", background=t["sidebar"], foreground=t["fg"], fieldbackground=t["sidebar"], borderwidth=0, rowheight=max(22, self.ui_size * 2 + 4), font=self.ui_font, relief="flat")
        style.map("Treeview", background=[("selected", t["sel"])], foreground=[("selected", t["fg"])])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("TScrollbar", background=t["bar"], troughcolor=t["bg"], bordercolor=t["bg"], arrowsize=10, relief="flat", width=10)
        style.map("TScrollbar", background=[("active", t["muted"])])
        style.configure("TPanedwindow", background=t["bar"])
        style.configure("Sash", sashthickness=3, gripcount=0)
        style.configure("TFrame", background=t["bar"])
        style.configure("TLabel", background=t["bar"], foreground=t["fg"], font=self.ui_font)

    def _build(self):
        self._menus()
        self.paned = ttk.Panedwindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True)
        self.side = tk.Frame(self.paned, bg=self.t["sidebar"], width=240)
        self.side_head = tk.Label(self.side, text="폴더", anchor="w", padx=12, pady=8)
        self.side_head.pack(fill="x")
        self.side_rule = tk.Frame(self.side, height=1, bd=0)
        self.side_rule.pack(fill="x")
        self.side_body = tk.Frame(self.side, bg=self.t["sidebar"])
        self.side_body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(self.side_body, show="tree", selectmode="browse")
        tsb = ttk.Scrollbar(self.side_body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(4, 8))
        tsb.pack(side="right", fill="y", pady=(4, 8))
        self.tree.bind("<<TreeviewOpen>>", self._tree_open)
        self.tree.bind("<Double-1>", self._tree_open_file)
        self.tree.bind("<Return>", self._tree_open_file)
        if self.conf.get("sidebar", True):
            self.paned.add(self.side, weight=0)
        right = ttk.Frame(self.paned)
        self.paned.add(right, weight=1)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: (self.status(), self._focus_ed()))
        self.nb.bind("<Button-2>", self._close_at)
        self.nb.bind("<Control-Button-1>", self._close_at)
        self.nb.bind("<Button-3>", self._tab_menu)
        self.findbar = tk.Frame(self.root, padx=10, pady=8)
        self.find_var = tk.StringVar()
        self.repl_var = tk.StringVar()
        self.re_var = tk.BooleanVar(value=False)
        self.case_var = tk.BooleanVar(value=False)
        self.find_widgets = []
        self._find_label("찾기")
        self.find_entry = self._find_entry(self.find_var, 22)
        self._find_label("바꾸기")
        self.repl_entry = self._find_entry(self.repl_var, 18)
        self._find_check("정규식", self.re_var)
        self._find_check("대소문자", self.case_var)
        self._find_btn("다음", self.find_next)
        self._find_btn("바꾸기", self.replace_one)
        self._find_btn("모두", self.replace_all)
        self._find_btn("파일에서", self.find_files)
        self._find_btn("닫기", self.hide_find, kind="ghost")
        self.find_entry.bind("<Return>", lambda e: self.find_next())
        self.find_entry.bind("<Escape>", lambda e: self.hide_find())
        self.statusbar = tk.Frame(self.root, height=28)
        self.st_pos = tk.Label(self.statusbar, anchor="w")
        self.st_meta = tk.Label(self.statusbar, anchor="w")
        self.st_path = tk.Label(self.statusbar, anchor="e")
        self.st_pos.pack(side="left", padx=(12, 8), pady=5)
        self.st_meta.pack(side="left", padx=8, pady=5)
        self.st_path.pack(side="right", padx=12, pady=5)
        self.statusbar.pack(fill="x", side="bottom")
        self._paint_chrome()

    def _find_label(self, text):
        w = tk.Label(self.findbar, text=text)
        w.pack(side="left", padx=(8, 4))
        self.find_widgets.append(w)
        return w

    def _find_entry(self, var, width):
        w = tk.Entry(self.findbar, textvariable=var, width=width, relief="flat", bd=0, highlightthickness=1)
        w.pack(side="left", padx=4, ipady=4)
        self.find_widgets.append(w)
        return w

    def _find_check(self, text, var):
        w = tk.Checkbutton(self.findbar, text=text, variable=var, relief="flat", bd=0, highlightthickness=0, takefocus=0)
        w.pack(side="left", padx=6)
        self.find_widgets.append(w)
        return w

    def _find_btn(self, text, cmd, kind="default"):
        return self._chip(self.findbar, text, cmd, kind=kind)

    def _chip(self, parent, text, cmd, kind="default"):
        w = self._make_chip(parent, text, cmd, kind)
        w.pack(side="left", padx=3)
        self.find_widgets.append(w)
        return w

    def _make_chip(self, parent, text, cmd, kind="default"):
        w = tk.Label(parent, text=text, padx=14, pady=5, cursor="hand2", highlightthickness=1)
        w._chip = kind
        w.bind("<Button-1>", lambda e, fn=cmd: fn())
        self._paint_chip(w)
        return w

    def _paint_chip(self, w):
        t = self.t
        kind = getattr(w, "_chip", "default")
        if kind == "ghost":
            rest_bg, rest_fg, border = t["bar"], t["muted"], t["bar"]
        else:
            rest_bg, rest_fg, border = t["btn"], t["fg"], t["border"]
        w.configure(
            bg=rest_bg, fg=rest_fg, font=self.ui_small,
            highlightbackground=border, highlightcolor=border,
        )
        w.bind("<Enter>", lambda e: w.configure(bg=t["sel"], fg=t["fg"], highlightbackground=t["keyword"]))
        w.bind("<Leave>", lambda e, bg=rest_bg, fg=rest_fg, bd=border: w.configure(bg=bg, fg=fg, highlightbackground=bd))

    def _paint_chrome(self):
        t = self.t
        self.side.configure(bg=t["sidebar"])
        self.side_head.configure(bg=t["sidebar"], fg=t["muted"], font=self.ui_small)
        self.side_rule.configure(bg=t["border"])
        self.side_body.configure(bg=t["sidebar"])
        self.findbar.configure(bg=t["bar"])
        self.statusbar.configure(bg=t["status_bg"])
        for lab in (self.st_pos, self.st_meta, self.st_path):
            lab.configure(bg=t["status_bg"], fg=t["status_fg"], font=self.ui_small)
        for w in self.find_widgets:
            if isinstance(w, tk.Entry):
                w.configure(
                    bg=t["field"], fg=t["fg"], insertbackground=t["caret"],
                    font=self.ui_font, highlightbackground=t["border"], highlightcolor=t["keyword"],
                )
            elif isinstance(w, tk.Checkbutton):
                w.configure(
                    bg=t["bar"], fg=t["muted"], activebackground=t["bar"], activeforeground=t["fg"],
                    selectcolor=t["bar"], font=self.ui_small,
                )
            elif getattr(w, "_chip", None):
                self._paint_chip(w)
            else:
                w.configure(bg=t["bar"], fg=t["muted"], font=self.ui_small)

    def _menus(self):
        m = tk.Menu(self.root)
        self.root.config(menu=m)
        filem = tk.Menu(m, tearoff=0)
        m.add_cascade(label="파일", menu=filem)
        filem.add_command(label="새 파일", accelerator=f"{MOD}+N", command=self.new_tab)
        filem.add_command(label="열기...", accelerator=f"{MOD}+O", command=self.open_dialog)
        filem.add_command(label="폴더 열기...", accelerator=f"{MOD}+Shift+O", command=self.open_folder_dialog)
        self.recent_menu = tk.Menu(filem, tearoff=0)
        filem.add_cascade(label="최근 파일", menu=self.recent_menu)
        self._rebuild_recent()
        filem.add_separator()
        filem.add_command(label="저장", accelerator=f"{MOD}+S", command=self.save)
        filem.add_command(label="다른 이름으로 저장...", accelerator=f"{MOD}+Shift+S", command=self.save_as)
        filem.add_command(label="다시 불러오기", command=self.reload)
        filem.add_separator()
        filem.add_command(label="탭 닫기", accelerator=f"{MOD}+W", command=self.close_tab)
        filem.add_separator()
        filem.add_command(label="설정...", accelerator=f"{MOD}+,", command=self.show_settings)
        filem.add_command(label="종료", accelerator=f"{MOD}+Q", command=self.quit)

        edit = tk.Menu(m, tearoff=0)
        m.add_cascade(label="편집", menu=edit)
        edit.add_command(label="실행 취소", accelerator=f"{MOD}+Z", command=lambda: self._ed() and self._ed().text.edit_undo())
        edit.add_command(label="다시 실행", accelerator=f"{MOD}+Shift+Z", command=lambda: self._ed() and self._ed().text.edit_redo())
        edit.add_separator()
        edit.add_command(label="잘라내기", accelerator=f"{MOD}+X", command=lambda: self._ed() and self._ed().text.event_generate("<<Cut>>"))
        edit.add_command(label="복사", accelerator=f"{MOD}+C", command=lambda: self._ed() and self._ed().text.event_generate("<<Copy>>"))
        edit.add_command(label="붙여넣기", accelerator=f"{MOD}+V", command=lambda: self._ed() and self._ed().text.event_generate("<<Paste>>"))
        edit.add_command(label="모두 선택", accelerator=f"{MOD}+A", command=lambda: self._ed() and self._ed().text.tag_add("sel", "1.0", "end-1c"))
        edit.add_separator()
        edit.add_command(label="줄 복제", accelerator=f"{MOD}+D", command=lambda: self._ed() and self._ed().duplicate_line())
        edit.add_command(label="줄 삭제", accelerator=f"{MOD}+Shift+K", command=lambda: self._ed() and self._ed().delete_line())
        edit.add_command(label="주석 토글", accelerator=f"{MOD}+/", command=lambda: self._ed() and self._ed().toggle_line_comment())
        edit.add_command(label="대문자", command=lambda: self._ed() and self._ed().change_case(True))
        edit.add_command(label="소문자", command=lambda: self._ed() and self._ed().change_case(False))
        edit.add_command(label="줄 끝 공백 제거", command=lambda: self._ed() and self._ed().trim_trailing())
        eol = tk.Menu(edit, tearoff=0)
        edit.add_cascade(label="줄바꿈 변환", menu=eol)
        eol.add_command(label="LF (Unix)", command=lambda: self._set_eol("\n"))
        eol.add_command(label="CRLF (Windows)", command=lambda: self._set_eol("\r\n"))
        eol.add_command(label="CR (old Mac)", command=lambda: self._set_eol("\r"))

        search = tk.Menu(m, tearoff=0)
        m.add_cascade(label="검색", menu=search)
        search.add_command(label="찾기", accelerator=f"{MOD}+F", command=self.show_find)
        search.add_command(label="다음 찾기", accelerator="F3", command=self.find_next)
        search.add_command(label="줄로 이동", accelerator=f"{MOD}+L", command=self.goto_line)
        search.add_command(label="파일에서 찾기", accelerator=f"{MOD}+Shift+F", command=self.find_files)
        search.add_separator()
        search.add_command(label="북마크 토글", accelerator=f"{MOD}+F2", command=lambda: self._ed() and self._ed().toggle_bookmark())
        search.add_command(label="다음 북마크", accelerator="F2", command=lambda: self._ed() and self._ed().next_bookmark())

        view = tk.Menu(m, tearoff=0)
        m.add_cascade(label="보기", menu=view)
        view.add_command(label="사이드바", accelerator=f"{MOD}+B", command=self.toggle_sidebar)
        view.add_command(label="자동 줄바꿈", command=self.toggle_wrap)
        view.add_command(label="확대", accelerator=f"{MOD}+=", command=lambda: self.zoom(1))
        view.add_command(label="축소", accelerator=f"{MOD}+-", command=lambda: self.zoom(-1))
        view.add_command(label="기본 크기", accelerator=f"{MOD}+0", command=lambda: self.zoom(0))
        view.add_separator()
        view.add_command(label="밝은 테마" if self.theme == "dark" else "어두운 테마", command=self.toggle_theme)

        helpm = tk.Menu(m, tearoff=0)
        m.add_cascade(label="도움말", menu=helpm)
        helpm.add_command(label="단축키", command=self.show_keys)

    def _bind(self):
        r, m = self.root, MOD

        def bind(seq, fn):
            r.bind(seq, lambda e: (fn() or True) and "break")

        bind(f"<{m}-n>", self.new_tab)
        bind(f"<{m}-o>", self.open_dialog)
        bind(f"<{m}-O>", self.open_folder_dialog)
        bind(f"<{m}-s>", self.save)
        bind(f"<{m}-S>", self.save_as)
        bind(f"<{m}-w>", self.close_tab)
        bind(f"<{m}-q>", self.quit)
        bind(f"<{m}-f>", self.show_find)
        bind(f"<{m}-comma>", self.show_settings)
        bind(f"<{m}-g>", self.find_next)
        bind(f"<{m}-l>", self.goto_line)
        bind(f"<{m}-b>", self.toggle_sidebar)
        bind(f"<{m}-d>", lambda: self._ed() and self._ed().duplicate_line())
        bind(f"<{m}-slash>", lambda: self._ed() and self._ed().toggle_line_comment())
        bind(f"<{m}-equal>", lambda: self.zoom(1))
        bind(f"<{m}-minus>", lambda: self.zoom(-1))
        bind(f"<{m}-0>", lambda: self.zoom(0))
        bind("<F3>", self.find_next)
        bind("<F2>", lambda: self._ed() and self._ed().next_bookmark())
        bind(f"<{m}-F2>", lambda: self._ed() and self._ed().toggle_bookmark())
        bind(f"<{m}-F>", self.find_files)
        bind("<Alt-Up>", lambda: self._ed() and self._ed().move_line(-1))
        bind("<Alt-Down>", lambda: self._ed() and self._ed().move_line(1))
        bind("<Option-Up>", lambda: self._ed() and self._ed().move_line(-1))
        bind("<Option-Down>", lambda: self._ed() and self._ed().move_line(1))
        bind(f"<{m}-Shift-k>", lambda: self._ed() and self._ed().delete_line())
        bind(f"<{m}-Shift-K>", lambda: self._ed() and self._ed().delete_line())

    def _mac_hooks(self):
        if sys.platform != "darwin":
            return
        for name, fn in (
            ("tk::mac::OpenDocument", self._open_docs),
            ("tk::mac::ShowPreferences", self.show_settings),
            ("tk::mac::Quit", self.quit),
        ):
            try:
                self.root.createcommand(name, fn)
            except tk.TclError:
                pass

    def _open_docs(self, *paths):
        for p in paths:
            path = Path(p)
            if path.is_dir():
                self.open_folder(path)
            elif path.exists():
                self.open_path(path)

    def _ed(self) -> Editor | None:
        try:
            w = self.nb.nametowidget(self.nb.select())
        except tk.TclError:
            return None
        return w if isinstance(w, Editor) else None

    def _focus_ed(self):
        ed = self._ed()
        if ed:
            ed.text.focus_set()
            self.refresh_tab(ed)

    def new_tab(self, _=None):
        ed = Editor(self.nb, self)
        self.editors.append(ed)
        self.nb.add(ed, text=ed.title())
        self.nb.select(ed)
        ed.text.focus_set()
        self.status()
        return ed

    def refresh_tab(self, ed: Editor):
        try:
            self.nb.tab(ed, text=ed.title())
        except tk.TclError:
            pass
        self.root.title(f"{ed.title()} — {APP_NAME}")

    def open_dialog(self):
        for p in filedialog.askopenfilenames(parent=self.root):
            self.open_path(Path(p))

    def open_folder_dialog(self):
        p = filedialog.askdirectory(parent=self.root)
        if p:
            self.open_folder(Path(p))

    def open_folder(self, path: Path):
        self.folder = path
        if str(self.side) not in self.paned.panes():
            self.paned.insert(0, self.side, weight=0)
        self._fill_tree(path)

    def _fill_tree(self, path: Path):
        self.tree.delete(*self.tree.get_children())
        self.side_head.configure(text=path.name)
        self._tree_populate("", path)

    def _tree_populate(self, node, path: Path):
        try:
            kids = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for p in kids:
            if p.is_dir() and skip_dir(p.name):
                continue
            if p.name.startswith(".") and p.name not in {".env", ".gitignore"} and p.is_dir():
                continue
            iid = self.tree.insert(node, "end", text=p.name + ("/" if p.is_dir() else ""), values=[str(p)])
            if p.is_dir():
                self.tree.insert(iid, "end", text="...")

    def _tree_open(self, _=None):
        iid = self.tree.focus()
        if not iid:
            return
        vals = self.tree.item(iid, "values")
        if not vals:
            return
        path = Path(vals[0])
        kids = self.tree.get_children(iid)
        if len(kids) == 1 and self.tree.item(kids[0], "text") == "...":
            self.tree.delete(kids[0])
            if path.is_dir():
                self._tree_populate(iid, path)

    def _tree_open_file(self, _=None):
        iid = self.tree.focus()
        if not iid:
            return
        vals = self.tree.item(iid, "values")
        if not vals:
            return
        path = Path(vals[0])
        if path.is_file():
            self.open_path(path)
        elif path.is_dir():
            self.tree.item(iid, open=True)
            self._tree_open()

    def open_path(self, path: Path):
        path = path.expanduser()
        try:
            path = path.resolve()
        except OSError:
            path = path.absolute()
        for ed in self.editors:
            if ed.path == path:
                self.nb.select(ed)
                return
        try:
            raw = path.read_bytes()
        except OSError as e:
            messagebox.showerror("열기 실패", str(e), parent=self.root)
            return
        if len(raw) > MAX_OPEN_WARN:
            if not messagebox.askokcancel("큰 파일", f"{path.name} 이 {len(raw) // 1_000_000}MB입니다. 열까요?", parent=self.root):
                return
        try:
            text, enc, eol = decode_bytes(raw)
        except ValueError:
            messagebox.showerror("열기 실패", "바이너리 파일은 열 수 없습니다.", parent=self.root)
            return
        ed = self.new_tab()
        ed.path = path
        ed.encoding = enc
        ed.eol = eol
        ed.lang = detect_lang(path)
        ed.text.insert("1.0", text)
        ed.saved = ed.content()
        ed.text.edit_reset()
        ed.text.edit_modified(False)
        ed.highlight()
        ed.redraw_gutter()
        self.refresh_tab(ed)
        self._push_recent(path)
        self.status()
        if self.folder is None and path.parent.is_dir():
            self.open_folder(path.parent)

    def _push_recent(self, path: Path):
        s = str(path)
        self.recent = [s] + [p for p in self.recent if p != s]
        self.recent = self.recent[:15]
        self._rebuild_recent()

    def _rebuild_recent(self):
        self.recent_menu.delete(0, "end")
        if not self.recent:
            self.recent_menu.add_command(label="(없음)", state="disabled")
            return
        for p in self.recent:
            self.recent_menu.add_command(label=p, command=lambda q=p: Path(q).exists() and self.open_path(Path(q)))

    def save(self, _=None) -> bool:
        ed = self._ed()
        if not ed:
            return False
        if not ed.path:
            return self.save_as()
        return self._write(ed, ed.path)

    def save_as(self, _=None) -> bool:
        ed = self._ed()
        if not ed:
            return False
        p = filedialog.asksaveasfilename(parent=self.root, initialfile=ed.path.name if ed.path else "untitled.txt")
        if not p:
            return False
        path = Path(p)
        if self._write(ed, path):
            ed.path = path
            ed.lang = detect_lang(path)
            ed.highlight()
            self.refresh_tab(ed)
            self._push_recent(path)
            return True
        return False

    def _write(self, ed: Editor, path: Path) -> bool:
        data = encode_for_save(ed.content(), ed.encoding, ed.eol)
        tmp = path.with_name(path.name + ".textpresstmp")
        try:
            tmp.write_bytes(data)
            tmp.replace(path)
        except OSError as e:
            messagebox.showerror("저장 실패", str(e), parent=self.root)
            try:
                tmp.unlink()
            except OSError:
                pass
            return False
        ed.path = path
        ed.saved = ed.content()
        self.refresh_tab(ed)
        self.status()
        return True

    def reload(self):
        ed = self._ed()
        if not ed or not ed.path:
            return
        if ed.dirty() and not messagebox.askokcancel("다시 불러오기", "저장하지 않은 내용이 사라집니다.", parent=self.root):
            return
        path = ed.path
        self.close_tab(force=True)
        self.open_path(path)

    def close_tab(self, _=None, force=False, ed: Editor | None = None):
        ed = ed or self._ed()
        if not ed:
            return
        if not force and ed.dirty():
            ans = messagebox.askyesnocancel("저장", f"{ed.title()} 을(를) 저장할까요?", parent=self.root)
            if ans is None:
                return
            if ans and not self.save():
                return
        self.nb.forget(ed)
        self.editors.remove(ed)
        ed.destroy()
        if not self.editors:
            self.new_tab()
        self.status()

    def _close_at(self, e):
        try:
            i = self.nb.index(f"@{e.x},{e.y}")
        except tk.TclError:
            return
        ed = self.nb.nametowidget(self.nb.tabs()[i])
        self.close_tab(ed=ed)

    def _tab_menu(self, e):
        try:
            i = self.nb.index(f"@{e.x},{e.y}")
        except tk.TclError:
            return
        ed = self.nb.nametowidget(self.nb.tabs()[i])
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="닫기", command=lambda: self.close_tab(ed=ed))
        menu.add_command(label="다른 탭 닫기", command=lambda: [self.close_tab(ed=x) for x in list(self.editors) if x is not ed])
        if ed.path:
            menu.add_command(label="경로 복사", command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append(str(ed.path))))
            if sys.platform == "darwin":
                menu.add_command(label="Finder에서 보기", command=lambda: os.system("open -R " + repr(str(ed.path))))
        menu.tk_popup(e.x_root, e.y_root)

    def show_find(self, _=None):
        if not self.findbar.winfo_ismapped():
            self.findbar.pack(fill="x", side="bottom", before=self.statusbar)
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")
        ed = self._ed()
        if ed:
            try:
                sel = ed.text.get("sel.first", "sel.last")
                if sel and "\n" not in sel:
                    self.find_var.set(sel)
            except tk.TclError:
                pass

    def hide_find(self):
        self.findbar.pack_forget()
        ed = self._ed()
        if ed:
            ed.text.tag_remove("find", "1.0", "end")
            ed.text.focus_set()

    def find_next(self, _=None):
        ed = self._ed()
        if not ed:
            return
        ok = ed.find_next(self.find_var.get(), self.re_var.get(), self.case_var.get())
        n = ed.mark_all(self.find_var.get(), self.re_var.get(), self.case_var.get())
        self.st_meta.configure(text="없음" if not ok else f"{n}개 일치")

    def replace_one(self):
        ed = self._ed()
        if ed:
            ed.replace_one(self.find_var.get(), self.repl_var.get(), self.re_var.get(), self.case_var.get())

    def replace_all(self):
        ed = self._ed()
        if not ed:
            return
        n = ed.replace_all(self.find_var.get(), self.repl_var.get(), self.re_var.get(), self.case_var.get())
        self.st_meta.configure(text=f"{n}개 바꿈")

    def find_files(self, _=None):
        if not self.folder:
            messagebox.showinfo("파일에서 찾기", "먼저 폴더를 여세요.", parent=self.root)
            return
        pat = self.find_var.get() or simpledialog.askstring("파일에서 찾기", "검색어", parent=self.root)
        if not pat:
            return
        try:
            hits = find_in_files(self.folder, pat, self.re_var.get(), self.case_var.get())
        except re.error as e:
            messagebox.showerror("정규식", str(e), parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title(f"파일에서 찾기 — {len(hits)}건")
        win.geometry("720x360")
        t = self.t
        win.configure(bg=t["bg"])
        lb = tk.Listbox(
            win, font=self.ui_font, bg=t["bg"], fg=t["fg"],
            selectbackground=t["sel"], selectforeground=t["fg"],
            relief="flat", bd=0, highlightthickness=0, activestyle="none",
        )
        lb.pack(fill="both", expand=True)
        for p, i, line in hits:
            try:
                rel = p.relative_to(self.folder)
            except ValueError:
                rel = p
            lb.insert("end", f"{rel}:{i}: {line}")

        def open_hit(_=None):
            sel = lb.curselection()
            if not sel:
                return
            p, i, _line = hits[sel[0]]
            self.open_path(p)
            ed = self._ed()
            if ed:
                ed.goto(i)

        lb.bind("<Double-1>", open_hit)
        lb.bind("<Return>", open_hit)

    def goto_line(self, _=None):
        ed = self._ed()
        if not ed:
            return
        n = simpledialog.askinteger("줄로 이동", "줄 번호", parent=self.root, minvalue=1)
        if n:
            ed.goto(n)

    def toggle_sidebar(self, _=None):
        if str(self.side) in self.paned.panes():
            self.paned.forget(self.side)
        else:
            self.paned.insert(0, self.side, weight=0)

    def toggle_wrap(self, _=None):
        self.wrap = not self.wrap
        for ed in self.editors:
            ed.text.configure(wrap="word" if self.wrap else "none")

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.t = THEMES[self.theme]
        self._mac_appear()
        self._style()
        self._paint_chrome()
        for ed in self.editors:
            ed.apply_theme()
        self._menus()
        self.persist()

    def zoom(self, delta: int):
        if delta == 0:
            self.font_size = 13
        else:
            self.font_size = max(9, min(28, self.font_size + delta))
        self.font.configure(size=self.font_size)
        self.gutter_font.configure(size=max(10, self.font_size - 1))
        for ed in self.editors:
            ed.apply_theme()
            ed.redraw_gutter()

    def _set_eol(self, eol: str):
        ed = self._ed()
        if ed:
            ed.eol = eol
            self.status()

    def show_keys(self):
        messagebox.showinfo(
            "단축키",
            f"{MOD}+N 새 파일    {MOD}+O 열기    {MOD}+S 저장    {MOD}+W 닫기\n"
            f"{MOD}+F 찾기    F3 다음    {MOD}+L 줄 이동    {MOD}+Shift+F 파일에서 찾기\n"
            f"{MOD}+D 줄 복제    {MOD}+/ 주석    Alt+Up/Down 줄 이동    {MOD}+B 사이드바\n"
            f"{MOD}+=/- 확대축소    F2 북마크    탭 중클릭으로 닫기",
            parent=self.root,
        )

    def status(self, _=None):
        ed = self._ed()
        if not ed:
            self.st_pos.configure(text="")
            self.st_meta.configure(text="")
            self.st_path.configure(text="")
            return
        try:
            line, col = ed.text.index("insert").split(".")
        except tk.TclError:
            return
        n = len(ed.content())
        eol = {"\n": "LF", "\r\n": "CRLF", "\r": "CR"}.get(ed.eol, "LF")
        path = str(ed.path) if ed.path else "제목 없음"
        self.st_pos.configure(text=f"{int(line):>4}:{int(col)+1:<3}")
        self.st_meta.configure(text=f"{ed.encoding.upper()}  ·  {ed.lang}  ·  {eol}  ·  {n}자")
        self.st_path.configure(text=path)
        self.refresh_tab(ed)

    def _mono_fonts(self) -> list[str]:
        have = set(tkfont.families())
        prefer = [
            "D2Coding", "Maple Mono", "Maple Mono NF CN", "Menlo", "SF Mono",
            "JetBrains Mono", "JetBrainsMono Nerd Font Mono", "PT Mono", "Andale Mono", "Courier",
        ]
        out = [n for n in prefer if n in have]
        extra = sorted(n for n in have if "Mono" in n and n not in out)
        return out + extra

    def show_settings(self, _=None):
        if getattr(self, "_prefs", None) is not None:
            try:
                if self._prefs.winfo_exists():
                    self._prefs.lift()
                    self._prefs.focus_set()
                    return
            except tk.TclError:
                pass
        t = self.t
        win = tk.Toplevel(self.root)
        self._prefs = win
        win.title("설정")
        win.geometry("440x540")
        win.resizable(False, False)
        win.configure(bg=t["bar"])
        try:
            win.tk.call("::tk::unsupported::MacWindowStyle", "appearance", win, "darkaqua" if self.theme == "dark" else "aqua")
        except tk.TclError:
            pass

        pad = {"bg": t["bar"], "fg": t["fg"], "font": self.ui_font, "anchor": "w"}
        muted = {**pad, "fg": t["muted"], "font": self.ui_small}
        body = tk.Frame(win, bg=t["bar"], padx=24, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=APP_NAME, **pad).pack(fill="x")
        tk.Label(body, text="글꼴과 테마는 바로 적용됩니다.", **muted).pack(fill="x", pady=(0, 16))

        def row(label):
            fr = tk.Frame(body, bg=t["bar"])
            fr.pack(fill="x", pady=6)
            tk.Label(fr, text=label, width=12, **pad).pack(side="left")
            return fr

        theme_fr = row("테마")
        theme_var = tk.StringVar(value=self.theme)

        def set_theme():
            if theme_var.get() != self.theme:
                self.toggle_theme()
                self.persist()

        for val, lab in (("dark", "어두움"), ("light", "밝음")):
            tk.Radiobutton(
                theme_fr, text=lab, value=val, variable=theme_var, command=set_theme,
                bg=t["bar"], fg=t["fg"], selectcolor=t["bar"], activebackground=t["bar"],
                activeforeground=t["fg"], font=self.ui_font, highlightthickness=0,
            ).pack(side="left", padx=(0, 12))

        fonts = self._mono_fonts() or [self.font_family]
        font_var = tk.StringVar(value=self.font_family if self.font_family in fonts else fonts[0])
        font_fr = row("글꼴")
        font_om = tk.OptionMenu(font_fr, font_var, *fonts)
        font_om.configure(bg=t["btn"], fg=t["fg"], activebackground=t["sel"], highlightthickness=0, font=self.ui_small, bd=0)
        font_om["menu"].configure(bg=t["bar"], fg=t["fg"], font=self.ui_small)
        font_om.pack(side="left", fill="x", expand=True)

        size_fr = row("편집기")
        size_var = tk.IntVar(value=self.font_size)
        size_sp = tk.Spinbox(size_fr, from_=9, to=28, textvariable=size_var, width=5, font=self.ui_font, relief="flat",
                             bg=t["field"], fg=t["fg"], highlightthickness=1, highlightbackground=t["border"])
        size_sp.pack(side="left")

        ui_fr = row("화면 글자")
        ui_var = tk.IntVar(value=self.ui_size)
        ui_sp = tk.Spinbox(ui_fr, from_=9, to=16, textvariable=ui_var, width=5, font=self.ui_font, relief="flat",
                           bg=t["field"], fg=t["fg"], highlightthickness=1, highlightbackground=t["border"])
        ui_sp.pack(side="left")
        tk.Label(ui_fr, text="탭 · 사이드바 · 상태바", bg=t["bar"], fg=t["muted"], font=self.ui_small).pack(side="left", padx=10)

        tab_fr = row("탭 너비")
        tab_var = tk.IntVar(value=self.tab_width)
        for n in (2, 4, 8):
            tk.Radiobutton(
                tab_fr, text=str(n), value=n, variable=tab_var,
                bg=t["bar"], fg=t["fg"], selectcolor=t["bar"], activebackground=t["bar"],
                activeforeground=t["fg"], font=self.ui_font, highlightthickness=0,
                command=lambda: None,
            ).pack(side="left", padx=(0, 10))

        wrap_var = tk.BooleanVar(value=self.wrap)
        sess_var = tk.BooleanVar(value=self.restore_session)
        gut_var = tk.BooleanVar(value=self.show_gutter)
        syn_var = tk.BooleanVar(value=self.syntax)

        def check(text, var):
            w = tk.Checkbutton(
                body, text=text, variable=var, anchor="w",
                bg=t["bar"], fg=t["fg"], selectcolor=t["bar"], activebackground=t["bar"],
                activeforeground=t["fg"], font=self.ui_font, highlightthickness=0,
            )
            w.pack(fill="x", pady=4)
            return w

        check("자동 줄바꿈", wrap_var)
        check("마지막 파일 다시 열기", sess_var)
        check("줄 번호", gut_var)
        check("문법 강조", syn_var)

        def apply_now(*_):
            self.font_family = font_var.get()
            try:
                self.font_size = int(size_var.get())
                self.ui_size = max(9, min(16, int(ui_var.get())))
                self.tab_width = int(tab_var.get())
            except (TypeError, ValueError, tk.TclError):
                return
            self.restore_session = bool(sess_var.get())
            self.show_gutter = bool(gut_var.get())
            self.syntax = bool(syn_var.get())
            wrap = bool(wrap_var.get())
            if wrap != self.wrap:
                self.toggle_wrap()
            self.font.configure(family=self.font_family, size=self.font_size)
            self.gutter_font.configure(family=self.font_family, size=max(10, self.font_size - 1))
            self.ui_font.configure(size=self.ui_size)
            self.ui_small.configure(size=max(9, self.ui_size - 1))
            self._style()
            self._paint_chrome()
            for ed in self.editors:
                ed.apply_theme()
            self.persist()

        font_var.trace_add("write", apply_now)
        size_var.trace_add("write", apply_now)
        ui_var.trace_add("write", apply_now)
        tab_var.trace_add("write", apply_now)
        wrap_var.trace_add("write", apply_now)
        sess_var.trace_add("write", apply_now)
        gut_var.trace_add("write", apply_now)
        syn_var.trace_add("write", apply_now)

        close = self._make_chip(body, "닫기", win.destroy, kind="default")
        close.pack(anchor="e", pady=(18, 0))
        win.bind("<Escape>", lambda e: win.destroy())
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    def persist(self):
        try:
            geo = self.root.geometry()
        except tk.TclError:
            geo = self.conf.get("geometry", "1100x720")
        save_conf({
            "theme": self.theme,
            "wrap": self.wrap,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "ui_size": self.ui_size,
            "tab_width": self.tab_width,
            "restore_session": self.restore_session,
            "show_gutter": self.show_gutter,
            "syntax": self.syntax,
            "geometry": geo,
            "folder": str(self.folder) if self.folder else None,
            "sidebar": str(self.side) in self.paned.panes(),
            "recent": self.recent,
            "session": [str(ed.path) for ed in self.editors if ed.path],
        })

    def quit(self, _=None):
        for ed in list(self.editors):
            if ed.dirty():
                self.nb.select(ed)
                ans = messagebox.askyesnocancel("종료", f"{ed.title()} 을(를) 저장할까요?", parent=self.root)
                if ans is None:
                    return
                if ans and not self.save():
                    return
                ed.saved = ed.content()
        self.persist()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()
