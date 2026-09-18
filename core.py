"""Pure helpers for typad. No tkinter."""
from __future__ import annotations

import json
import keyword
import os
import re
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
}
APP_NAME = "typad"
CONF_PATH = Path.home() / "Library" / "Application Support" / "typad" / "config.json"
LEGACY_CONF_PATHS = (
    Path.home() / ".typad.json",
    Path.home() / ".txtr.json",
    Path.home() / ".textpress.json",
    Path.home() / ".texter.json",
)
MAX_HIGHLIGHT = 250_000
MAX_OPEN_WARN = 8_000_000

EXT = {
    ".py": "python", ".pyw": "python", ".js": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".json": "json", ".html": "html", ".htm": "html",
    ".xml": "xml", ".svg": "xml", ".css": "css", ".md": "markdown",
    ".markdown": "markdown", ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".toml": "toml", ".yml": "yaml", ".yaml": "yaml", ".sql": "sql",
    ".go": "go", ".rs": "rust", ".java": "java", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp", ".cs": "csharp",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
    ".lua": "lua", ".r": "r", ".txt": "text", ".log": "text",
    ".ini": "toml", ".cfg": "toml", ".env": "bash",
}

COMMENT = {
    "python": "# ", "bash": "# ", "yaml": "# ", "toml": "# ", "r": "# ",
    "javascript": "// ", "typescript": "// ", "c": "// ", "cpp": "// ",
    "java": "// ", "go": "// ", "rust": "// ", "csharp": "// ",
    "swift": "// ", "kotlin": "// ", "php": "// ", "json": "// ",
    "sql": "-- ", "lua": "-- ", "ruby": "# ",
}

DEFAULT_STRING = '"""[\\s\\S]*?"""|\'\'\'[\\s\\S]*?\'\'\'|"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\''
_JS_STR = '`(?:\\\\.|[^`\\\\])*`|"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\''
PY_BI = '\\b(?:print|len|range|open|int|str|list|dict|set|tuple|bool|type|isinstance|enumerate|zip|map|filter|sum|min|max|abs|sorted|object|super|input|format|None|True|False)\\b'
C_TYPES = '\\b(?:int|char|void|float|double|long|short|unsigned|signed|bool|size_t|string|auto)\\b'

def detect_lang(path: str | Path) -> str:
    return EXT.get(Path(path).suffix.lower(), "text")


def decode_bytes(raw: bytes) -> tuple[str, str, str]:
    if b"\0" in raw[:8192]:
        raise ValueError("binary file")
    if raw.startswith(b"\xef\xbb\xbf"):
        text, enc = raw.decode("utf-8-sig"), "utf-8-sig"
    else:
        text, enc = None, "utf-8"
        for cand in ("utf-8", "cp949", "latin-1"):
            try:
                text, enc = raw.decode(cand), cand
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", "replace")
    if "\r\n" in text:
        return text.replace("\r\n", "\n"), enc, "\r\n"
    if "\r" in text:
        return text.replace("\r", "\n"), enc, "\r"
    return text, enc, "\n"


def encode_for_save(text: str, encoding: str, eol: str) -> bytes:
    return text.replace("\n", eol).encode(encoding)


def toggle_comment(lines: list[str], prefix: str) -> list[str]:
    nonempty = [ln for ln in lines if ln.strip()]
    bare = prefix.rstrip()
    if nonempty and all(ln.lstrip().startswith(bare) for ln in nonempty):
        out = []
        for ln in lines:
            if not ln.strip():
                out.append(ln)
                continue
            i = ln.find(prefix)
            n = len(prefix)
            if i < 0:
                i = ln.find(bare)
                n = len(bare)
            out.append(ln[:i] + ln[i + n:] if i >= 0 else ln)
        return out
    return [prefix + ln if ln.strip() else ln for ln in lines]


def _kw(words: list[str]) -> str:
    return r"\b(?:" + "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True)) + r")\b"


def _lang(keywords: list[str], comment: str, extra_string: str = "", types: str = "") -> re.Pattern[str]:
    str_pat = extra_string or DEFAULT_STRING
    parts = [
        rf"(?P<comment>{comment})",
        rf"(?P<string>{str_pat})",
        r"(?P<number>\b0x[0-9A-Fa-f]+\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)",
    ]
    if types:
        parts.append(rf"(?P<type>{types})")
    parts.append(rf"(?P<keyword>{_kw(keywords)})")
    parts.append(r"(?P<func>\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())")
    return re.compile("|".join(parts), re.M)

_JS = '//.*?$|/\\*[\\s\\S]*?\\*/'
LANGS: dict[str, re.Pattern[str]] = {}
LANGS['python'] = _lang(keyword.kwlist + list(getattr(keyword, 'softkwlist', [])), '#.*?$', types=PY_BI)
LANGS['javascript'] = _lang(['break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends', 'false', 'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new', 'null', 'return', 'static', 'super', 'switch', 'this', 'throw', 'true', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'async', 'await', 'of', 'from'], '//.*?$|/\\*[\\s\\S]*?\\*/', extra_string=_JS_STR)
LANGS['typescript'] = _lang(['break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends', 'false', 'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new', 'null', 'return', 'static', 'super', 'switch', 'this', 'throw', 'true', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'async', 'await', 'of', 'from', 'type', 'interface', 'enum', 'implements', 'private', 'public', 'protected', 'readonly', 'abstract', 'as', 'is', 'namespace', 'declare', 'module'], '//.*?$|/\\*[\\s\\S]*?\\*/', extra_string=_JS_STR, types='\\b(?:string|number|boolean|any|void|never|unknown)\\b')
LANGS['c'] = _lang(['auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'inline', 'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while'], '//.*?$|/\\*[\\s\\S]*?\\*/', types=C_TYPES)
LANGS['cpp'] = _lang(['and', 'bool', 'break', 'case', 'catch', 'char', 'class', 'const', 'continue', 'default', 'delete', 'do', 'double', 'else', 'enum', 'explicit', 'extern', 'false', 'float', 'for', 'friend', 'goto', 'if', 'inline', 'int', 'long', 'mutable', 'namespace', 'new', 'operator', 'private', 'protected', 'public', 'register', 'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'template', 'this', 'throw', 'true', 'try', 'typedef', 'typename', 'union', 'unsigned', 'using', 'virtual', 'void', 'volatile', 'while', 'constexpr', 'nullptr'], '//.*?$|/\\*[\\s\\S]*?\\*/', types=C_TYPES)
LANGS['java'] = _lang(['abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 'extends', 'final', 'finally', 'float', 'for', 'if', 'implements', 'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new', 'package', 'private', 'protected', 'public', 'return', 'short', 'static', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 'transient', 'try', 'void', 'volatile', 'while', 'true', 'false', 'null', 'var', 'record'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['go'] = _lang(['break', 'case', 'chan', 'const', 'continue', 'default', 'defer', 'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import', 'interface', 'map', 'package', 'range', 'return', 'select', 'struct', 'switch', 'type', 'var', 'true', 'false', 'nil', 'iota'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['rust'] = _lang(['as', 'async', 'await', 'break', 'const', 'continue', 'crate', 'dyn', 'else', 'enum', 'extern', 'false', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'match', 'mod', 'move', 'mut', 'pub', 'ref', 'return', 'self', 'Self', 'static', 'struct', 'super', 'trait', 'true', 'type', 'unsafe', 'use', 'where', 'while'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['csharp'] = _lang(['abstract', 'as', 'base', 'bool', 'break', 'byte', 'case', 'catch', 'char', 'checked', 'class', 'const', 'continue', 'decimal', 'default', 'delegate', 'do', 'double', 'else', 'enum', 'event', 'explicit', 'extern', 'false', 'finally', 'fixed', 'float', 'for', 'foreach', 'goto', 'if', 'implicit', 'in', 'int', 'interface', 'internal', 'is', 'lock', 'long', 'namespace', 'new', 'null', 'object', 'operator', 'out', 'override', 'params', 'private', 'protected', 'public', 'readonly', 'ref', 'return', 'sbyte', 'sealed', 'short', 'sizeof', 'static', 'string', 'struct', 'switch', 'this', 'throw', 'true', 'try', 'typeof', 'uint', 'ulong', 'unchecked', 'unsafe', 'ushort', 'using', 'virtual', 'void', 'volatile', 'while', 'var', 'async', 'await'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['swift'] = _lang(['class', 'deinit', 'enum', 'extension', 'func', 'import', 'init', 'let', 'operator', 'private', 'protocol', 'public', 'static', 'struct', 'var', 'break', 'case', 'continue', 'default', 'do', 'else', 'for', 'guard', 'if', 'in', 'return', 'switch', 'where', 'while', 'as', 'catch', 'false', 'is', 'nil', 'super', 'self', 'throw', 'throws', 'true', 'try', 'async', 'await'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['kotlin'] = _lang(['as', 'break', 'class', 'continue', 'do', 'else', 'false', 'for', 'fun', 'if', 'in', 'interface', 'is', 'null', 'object', 'package', 'return', 'super', 'this', 'throw', 'true', 'try', 'val', 'var', 'when', 'while', 'catch', 'finally', 'import', 'abstract', 'data', 'enum', 'inner', 'internal', 'open', 'override', 'private', 'protected', 'public', 'sealed', 'suspend'], '//.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['php'] = _lang(['abstract', 'and', 'array', 'as', 'break', 'case', 'catch', 'class', 'clone', 'const', 'continue', 'declare', 'default', 'do', 'echo', 'else', 'elseif', 'empty', 'exit', 'extends', 'final', 'finally', 'fn', 'for', 'foreach', 'function', 'global', 'goto', 'if', 'implements', 'include', 'include_once', 'instanceof', 'interface', 'isset', 'list', 'namespace', 'new', 'or', 'print', 'private', 'protected', 'public', 'require', 'require_once', 'return', 'static', 'switch', 'throw', 'trait', 'try', 'unset', 'use', 'var', 'while', 'xor', 'yield', 'true', 'false', 'null'], '//.*?$|#.*?$|/\\*[\\s\\S]*?\\*/')
LANGS['ruby'] = _lang(['BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class', 'def', 'defined', 'do', 'else', 'elsif', 'end', 'ensure', 'false', 'for', 'if', 'in', 'module', 'next', 'nil', 'not', 'or', 'redo', 'rescue', 'retry', 'return', 'self', 'super', 'then', 'true', 'undef', 'unless', 'until', 'when', 'while', 'yield'], '#.*?$')
LANGS['sql'] = _lang(['select', 'from', 'where', 'insert', 'into', 'values', 'update', 'set', 'delete', 'create', 'table', 'drop', 'alter', 'and', 'or', 'not', 'null', 'as', 'join', 'left', 'right', 'inner', 'outer', 'on', 'group', 'by', 'order', 'asc', 'desc', 'limit', 'offset', 'having', 'union', 'all', 'distinct', 'into', 'primary', 'key', 'foreign', 'references', 'index', 'view'], '--.*?$')
LANGS['bash'] = _lang(['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'in', 'case', 'esac', 'function', 'return', 'exit', 'echo', 'export', 'local', 'readonly', 'set', 'unset', 'shift', 'test', 'true', 'false'], '#.*?$')
LANGS['yaml'] = _lang(['true', 'false', 'null', 'yes', 'no', 'on', 'off'], '#.*?$')
LANGS['toml'] = _lang(['true', 'false'], '#.*?$')
LANGS['lua'] = _lang(['and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while'], '--.*?$')
LANGS['r'] = _lang(['if', 'else', 'repeat', 'while', 'function', 'for', 'in', 'next', 'break', 'TRUE', 'FALSE', 'NULL', 'NA', 'Inf', 'NaN'], '#.*?$')
LANGS['json'] = re.compile('(?P<type>"(?:\\\\.|[^"\\\\])*"?(?=\\s*:))|(?P<string>"(?:\\\\.|[^"\\\\])*")|(?P<number>-?\\b\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?\\b)|(?P<keyword>\\b(?:true|false|null)\\b)')
LANGS['html'] = re.compile('(?P<comment><!--[\\s\\S]*?-->)|(?P<string>"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\')|(?P<keyword></?[\\w:-]+|/?>)|(?P<type>\\b[\\w:-]+(?=\\s*=))')
LANGS['xml'] = LANGS['html']
LANGS['css'] = re.compile('(?P<comment>/\\*[\\s\\S]*?\\*/)|(?P<string>"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\')|(?P<keyword>[.#]?[\\w-]+(?=\\s*\\{)|@(?:media|import|font-face|keyframes|charset))|(?P<type>\\b[\\w-]+(?=\\s*:))|(?P<number>#[0-9A-Fa-f]{3,8}|\\b\\d+(?:\\.\\d+)?(?:px|em|rem|%|vh|vw|s|ms)?\\b)')
LANGS['markdown'] = re.compile('(?P<string>```[\\s\\S]*?```|`[^`]+`)|(?P<keyword>^#{1,6} .*)$|(?P<func>\\[[^\\]]+\\]\\([^)]+\\))|(?P<comment>^> .*$)|(?P<type>\\*\\*[^*]+\\*\\*|\\*[^*]+\\*)', re.M)

def spans(text: str, lang: str):
    prog = LANGS.get(lang)
    if not prog:
        return
    for m in prog.finditer(text):
        kind = m.lastgroup
        if kind:
            yield kind, m.start(), m.end()


def skip_dir(name: str) -> bool:
    return name in SKIP_DIRS


def search_text(src: str, pat: str, regex: bool, case: bool, start: int = 0):
    flags = 0 if case else re.I
    rx = re.compile(pat if regex else re.escape(pat), flags)
    m = rx.search(src, start)
    if m is None and start:
        m = rx.search(src, 0)
    return m, rx


def replace_all_text(src: str, pat: str, repl: str, regex: bool, case: bool) -> tuple[str, int]:
    flags = 0 if case else re.I
    rx = re.compile(pat if regex else re.escape(pat), flags)
    return rx.subn(repl, src)


def find_in_files(root: Path, pattern: str, regex: bool, case: bool, limit: int = 500):
    flags = 0 if case else re.I
    rx = re.compile(pattern if regex else re.escape(pattern), flags)
    hits = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not skip_dir(d)]
        for name in files:
            p = Path(dirpath) / name
            try:
                if p.stat().st_size > 1_000_000:
                    continue
                raw = p.read_bytes()
            except OSError:
                continue
            if b"\0" in raw[:4096]:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("cp949")
                except UnicodeDecodeError:
                    continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append((p, i, line.strip()[:200]))
                    if len(hits) >= limit:
                        return hits
    return hits


def load_conf() -> dict:
    for path in (CONF_PATH, *LEGACY_CONF_PATHS):
        if not path.exists():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_conf(conf: dict) -> None:
    try:
        CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONF_PATH.write_text(json.dumps(conf, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# --- App Sandbox security-scoped bookmarks -------------------------------
#
# Only matters for a sandboxed build (the App Store track). tkinter's own
# file dialogs still trigger the native NSOpenPanel/NSSavePanel under the
# sandbox and work fine for the current session, but persisted access
# across relaunches -- session restore, the recent-files list, the last
# browsed folder -- needs a security-scoped bookmark taken right after the
# panel grants access. Everything here is a no-op when PyObjC's Cocoa
# bridge isn't importable, which is true for every non-sandboxed build
# (the notarized direct-distribution app, the standalone py2app build
# without the sandbox entitlement, and plain `python3 texter.py`).
try:
    from Foundation import NSData, NSURL  # type: ignore

    HAVE_COCOA = True
except Exception:  # pragma: no cover - exercised only without PyObjC
    HAVE_COCOA = False

_BOOKMARK_CREATE_WITH_SECURITY_SCOPE = 1 << 11
_BOOKMARK_RESOLVE_WITH_SECURITY_SCOPE = 1 << 10


def make_bookmark(path: Path) -> str | None:
    """Create a base64 security-scoped bookmark for ``path``.

    Returns None outside the sandbox, without PyObjC, or if the process
    does not currently hold sandbox access to ``path`` (for example a
    path that was never chosen through a mediated open/save panel).
    Callers should treat None exactly like "no bookmark available" and
    fall back to the plain path, which is what every existing caller
    already does.
    """
    if not HAVE_COCOA:
        return None
    try:
        import base64

        url = NSURL.fileURLWithPath_(str(path))
        data, _error = url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
            _BOOKMARK_CREATE_WITH_SECURITY_SCOPE, None, None, None,
        )
        if not data:
            return None
        return base64.b64encode(bytes(data)).decode("ascii")
    except Exception:
        return None


class ScopedAccess:
    """Context manager around ``NSURL`` security-scoped resource access.

    A no-op everywhere PyObjC/Cocoa is unavailable or ``bookmark_b64`` is
    falsy, so every call site behaves identically in non-sandboxed
    builds. Safe to enter more than once; ``stop`` is idempotent.
    """

    def __init__(self, bookmark_b64: str | None):
        self._bookmark = bookmark_b64
        self._url = None
        self._active = False

    def __enter__(self) -> "ScopedAccess":
        self.start()
        return self

    def __exit__(self, *exc) -> bool:
        self.stop()
        return False

    def start(self) -> bool:
        if self._active or not HAVE_COCOA or not self._bookmark:
            return self._active
        try:
            import base64

            raw = base64.b64decode(self._bookmark)
            ns_data = NSData.dataWithBytes_length_(raw, len(raw))
            url, _stale, _error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
                ns_data, _BOOKMARK_RESOLVE_WITH_SECURITY_SCOPE, None, None, None,
            )
            if url is not None and url.startAccessingSecurityScopedResource():
                self._url = url
                self._active = True
        except Exception:
            self._active = False
        return self._active

    def stop(self) -> None:
        if self._active and self._url is not None:
            try:
                self._url.stopAccessingSecurityScopedResource()
            except Exception:
                pass
        self._active = False
        self._url = None
