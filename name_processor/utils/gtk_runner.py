from collections.abc import Generator, Callable
from typing import Any

from gi.repository import GLib


def run_in_idle_loop(
    generator: Generator, on_complete: Callable[[Any], None] | None = None
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
