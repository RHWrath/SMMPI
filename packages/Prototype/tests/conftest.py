"""
Shared pytest configuration for SMMPI tests.

Module stubs:
    image_to_video.py (and other source modules) import from ui_setup and
    adb_setup, which in turn import customtkinter, tkinter, ppadb. These
    are heavy GUI / device-comms dependencies that unit tests don't need.

    We stub them in sys.modules BEFORE any test tries to import the
    source modules. The stubs only need to exist — unit tests for image
    processing logic never call into GUI or ADB paths.

    If a test does need one of these for a specific feature, it can
    patch the stub with real behaviour locally.
"""

import sys
import types


class _Stub:
    """Anything attribute-accessed or called on this returns another _Stub."""
    def __getattr__(self, item):
        return _Stub()

    def __call__(self, *args, **kwargs):
        return _Stub()


def _make_stub_module(name):
    module = types.ModuleType(name)
    module.__getattr__ = lambda item: _Stub()  # type: ignore[attr-defined]
    return module


for _mod_name in [
    "customtkinter",
    "tkinter",
    "tkinter.messagebox",
    "ppadb",
    "ppadb.client",
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub_module(_mod_name)