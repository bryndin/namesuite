from typing import NamedTuple


# Given Names store column indices (Tab 1 - Rename Given Names)
# Important: Order must match the actual column definitions in the GTK store
# Note: `handle` column is internal and not displayed in the UI
class GivenRowData(NamedTuple):
    checkbox: bool
    gramps_id: str
    display_name: str
    current: str
    proposed: str
    alt_action: str
    handle: str
