"""ReferenceManager — composes the reference persistence mixins."""

from typing import TYPE_CHECKING, Optional

from med_paper_assistant.domain.services.reference_converter import (
    ReferenceConverter,
)

from ._artifacts import ArtifactMixin
from ._citation import CitationFormatMixin
from ._content import ContentMarkdownMixin
from ._content_body import ContentBodyMixin
from ._deletion import ReferenceDeletionMixin
from ._foam_asset_fragment import FoamAssetFragmentMixin
from ._foam_asset_note_body import FoamAssetNoteBodyMixin
from ._foam_asset_notes import FoamAssetNotesMixin
from ._foam_assets import FoamAssetSourceMixin
from ._foam_context import FoamContextMixin
from ._foam_draft import FoamDraftNotesMixin
from ._foam_index import FoamIndexMixin
from ._foam_library import FoamLibraryMixin
from ._foam_library_overview import FoamLibraryOverviewMixin
from ._foam_notes import FoamNoteWriterMixin
from ._foam_pages import FoamPageBodyMixin
from ._foam_publish import FoamPublishMixin
from ._foam_snapshots import FoamSnapshotMixin
from ._foam_tags import FoamTagMixin
from ._foam_wiki import FoamWikiMixin
from ._fulltext import FulltextMixin
from ._identity import IdentityMixin
from ._intake import LocalIntakeMixin
from ._intake_payload import IntakePayloadMixin
from ._paths import PathsMixin
from ._payload import PayloadNormalizerMixin
from ._queries import ReferenceQueryMixin
from ._resolution import IdentityResolutionMixin
from ._save import SaveReferenceMixin
from ._save_mcp import VerifiedSaveMixin
from ._storage import MetadataStoreMixin
from ._text_utils import TextUtilsMixin

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager


class ReferenceManager(
    PathsMixin,
    TextUtilsMixin,
    IdentityMixin,
    IdentityResolutionMixin,
    PayloadNormalizerMixin,
    MetadataStoreMixin,
    ReferenceDeletionMixin,
    ReferenceQueryMixin,
    SaveReferenceMixin,
    VerifiedSaveMixin,
    LocalIntakeMixin,
    IntakePayloadMixin,
    ArtifactMixin,
    CitationFormatMixin,
    ContentMarkdownMixin,
    ContentBodyMixin,
    FulltextMixin,
    FoamTagMixin,
    FoamNoteWriterMixin,
    FoamContextMixin,
    FoamLibraryMixin,
    FoamLibraryOverviewMixin,
    FoamPublishMixin,
    FoamPageBodyMixin,
    FoamSnapshotMixin,
    FoamWikiMixin,
    FoamDraftNotesMixin,
    FoamAssetSourceMixin,
    FoamAssetFragmentMixin,
    FoamAssetNoteBodyMixin,
    FoamAssetNotesMixin,
    FoamIndexMixin,
):
    """
    管理本地文獻參考資料的儲存、檢索和組織。

    重構說明 (2025-12):
    - 使用 ReferenceConverter Domain Service 處理格式轉換
    - 支援多來源：PubMed, Zotero, DOI
    - 唯一識別符：unique_id + citation_key (for Foam)
    - 文獻搜尋由外部 MCP 負責，Agent 協調資料傳遞
    """

    def __init__(
        self,
        base_dir: str = "references",
        project_manager: Optional["ProjectManager"] = None,
        pubmed_api_url: Optional[str] = None,
    ):
        """
        Initialize the ReferenceManager.

        Args:
            base_dir: Default directory to store references (used if no project active).
            project_manager: Optional ProjectManager for multi-project support.
            pubmed_api_url: URL for pubmed-search HTTP API (MCP-to-MCP communication).
        """
        self._default_base_dir = base_dir
        self._project_manager = project_manager
        self._converter = ReferenceConverter()
        self._pubmed_api_url = pubmed_api_url
        # Note: Directory is created on-demand when saving references,
        # not at initialization to avoid polluting root directory
