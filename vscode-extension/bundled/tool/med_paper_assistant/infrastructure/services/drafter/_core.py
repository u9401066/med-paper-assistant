"""Drafter: citation-aware draft creation, citation insertion and wikilink synchronisation."""

from ._wikilink_sync import WikilinkSyncMixin
from ._writing import DraftWritingMixin


class Drafter(DraftWritingMixin, WikilinkSyncMixin):
    pass
