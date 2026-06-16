from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TypeVar

from gi.repository import GLib

from name_processor.protocols.view import BackgroundTaskRunner

T = TypeVar("T")


class GtkBackgroundTaskRunner:
    """GTK implementation of BackgroundTaskRunner using GLib.idle_add."""

    def run_chunked(
        self,
        generator: Generator[None, None, T],
        on_complete: Callable[[T | None], None] | None = None,
    ) -> None:
        """
        Executes a chunked generator in the GTK idle loop to prevent UI freezing.

        :param generator: A generator yielding control periodically.
        :param on_complete: Callback executed with the generator's final return value.
        """

        def process_chunk() -> bool:
            try:
                next(generator)
                return True  # Tell GTK to keep calling this when idle
            except StopIteration as e:
                # Generator finished naturally
                if on_complete:
                    on_complete(e.value)
                return False  # Stop the idle loop
            except Exception as e:
                # Log or handle unexpected DB/Processing errors
                print(f"Background task failed: {e}")
                return False

        GLib.idle_add(process_chunk)
