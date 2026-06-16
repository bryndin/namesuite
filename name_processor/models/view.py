"""DEPRECATED: Row schemas moved to presentation.row_schemas.

This module provides backward compatibility by re-exporting row schemas.
Import from name_processor.presentation.row_schemas instead.
"""

# Backward compatibility re-exports
from name_processor.presentation.row_schemas import GivenRowData, AuditRowData

# TODO: Remove this module in future versions
__all__ = ["GivenRowData", "AuditRowData"]
