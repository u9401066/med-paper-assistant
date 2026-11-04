"""Reference manager package.

``ReferenceManager`` is composed from focused mixins, one module per
responsibility. Import it from this package, as before::

    from med_paper_assistant.infrastructure.persistence.reference_manager import (
        ReferenceManager,
    )
"""

from ._manager import ReferenceManager

__all__ = ["ReferenceManager"]
