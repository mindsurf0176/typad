"""py2app setup script for typad. Run on a clean macOS Python (GitHub
Actions macos runner), not through Homebrew, to avoid the environment
quirks documented in docs/app-store.md.

    python3 -m pip install py2app
    python3 setup.py py2app

Set TYPAD_SANDBOX=1 to build the App Sandbox variant instead (adds the
App Sandbox entitlement plus PyObjC's Cocoa bridge so core.py's
security-scoped bookmark helpers actually work under sandbox):

    python3 -m pip install py2app pyobjc-framework-Cocoa
    TYPAD_SANDBOX=1 python3 setup.py py2app
"""
import os

from setuptools import setup

APP = ["texter.py"]
DATA_FILES = []
SANDBOXED = os.environ.get("TYPAD_SANDBOX") == "1"

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "dist/AppIcon.icns",
    "plist": {
        "CFBundleName": "typad",
        "CFBundleDisplayName": "typad",
        "CFBundleIdentifier": "ai.minseo.typad",
        "CFBundleShortVersionString": "0.2.1",
        "CFBundleVersion": "1",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Copyright \u00a9 2026 Minseo Lee",
        "ITSAppUsesNonExemptEncryption": False,
    },
    "packages": [],
    "includes": ["core", "tkinter"] + (["Foundation"] if SANDBOXED else []),
}

setup(
    app=APP,
    name="typad",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"] + (["pyobjc-framework-Cocoa"] if SANDBOXED else []),
)
