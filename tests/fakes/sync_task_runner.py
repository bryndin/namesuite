from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TypeVar


T = TypeVar("T")


class SynchronousTaskRunner:
    """Synchronous implementation of BackgroundTaskRunner for testing."""

    def run_chunked(
        self,
        generator: Generator[None, None, T],
        on_complete: Callable[[T | None], None] | None = None,
    ) -> None:
        """
        Execute a generator synchronously to completion.

        This is intended for use in tests where we want deterministic
        behavior without the GTK main loop.

        Args:
            generator: A generator yielding control periodically.
            on_complete: Callback executed with the generator's final return value.
        """
        try:
            # Consume the entire generator
            while True:
                next(generator)
        except StopIteration as e:
            # Generator finished naturally
            if on_complete:
                on_complete(e.value)
        except Exception as e:
            # Propagate exceptions in tests (don't swallow them)
            raise RuntimeError(f"Synchronous task failed: {e}") from e
