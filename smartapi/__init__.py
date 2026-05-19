"""Local SmartApi shim to shadow the installed `SmartApi` package during tests.
This delegates to the lightweight `smartapi.smartConnect` shim included in the repo.
"""
from smartapi.smartConnect import SmartConnect

__all__ = ["SmartConnect"]
"""Local shim for smartapi to satisfy test imports in offline environments.
This provides a minimal `SmartConnect` interface used by the application during testing.
Do not rely on this for real order placement; in production the official SmartAPI
package must be installed and used.
"""
from .smartConnect import SmartConnect
