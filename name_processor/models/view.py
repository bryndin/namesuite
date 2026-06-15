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


# Audit store column indices (Tab 2 - Audit Patronymics)
# Important: Order must match the actual column definitions in the GTK store
# Note: `handle` column is internal and not displayed in the UI
class AuditRowData(NamedTuple):
    checkbox: bool
    display_name: str
    gramps_id: str
    father_name: str
    current_patronymic: str
    diff_markup: str
    confidence: str
    ref_year: str
    rule_id: str
    handle: str
    suggested_string: str
    explanation: str
