"""Ensures the bootstrap runs under pytest even if a test forgets to import it."""
import _bootstrap  # noqa: F401
