"""
Load Angel One SmartConnect from the official SDK only.

The repo must not contain a top-level package named `smartapi/` — that name
shadows modules inside the installed smartapi-python wheel and breaks login on
PythonAnywhere and other hosts when the app is run from the project directory.
"""

import os


def get_smart_connect_class():
    """Return the real SmartConnect class from smartapi-python."""
    try:
        from SmartApi.smartConnect import SmartConnect
    except ImportError as exc:
        if os.getenv("BALANCEWHEEL_USE_SMARTAPI_SHIM", "").strip().lower() in {"1", "true", "yes"}:
            from test_shims.smartapi_stub.smartConnect import SmartConnect
            return SmartConnect
        raise ImportError(
            "Angel One SDK not found. Install with: pip install 'smartapi-python>=1.5.5'"
        ) from exc

    # Reject the offline stub if it was somehow loaded
    if getattr(SmartConnect.generateSession, "__module__", "").startswith("test_shims"):
        raise ImportError(
            "Test SmartAPI shim is active; install smartapi-python>=1.5.5 for production."
        )
    return SmartConnect


SmartConnect = get_smart_connect_class()
