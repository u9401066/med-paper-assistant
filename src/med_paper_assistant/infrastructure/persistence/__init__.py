"""
Persistence Layer - Data storage and retrieval.
"""

from .checkpoint_manager import CheckpointManager
from .data_artifact_tracker import DataArtifactTracker
from .domain_constraint_engine import (
    ConstraintCategory,
    ConstraintViolation,
    DomainConstraintEngine,
)
from .draft_snapshot_manager import DraftSnapshotManager
from .evolution_verifier import EvolutionVerifier
from .file_storage import FileStorage
from .hook_effectiveness_tracker import HookEffectivenessTracker
from .meta_learning_engine import MetaLearningEngine
from .pipeline_gate_validator import GateResult, PipelineGateValidator
from .project_manager import ProjectManager, get_project_manager
from .project_memory_manager import ProjectMemoryManager
from .project_repository import ProjectRepository
from .quality_scorecard import QualityScorecard
from .reference_manager import ReferenceManager
from .reference_repository import ReferenceRepository
from .workspace_state_manager import (
    WorkspaceStateManager,
    get_workspace_state_manager,
    reset_workspace_state_manager,
)
from .writing_hooks import HookIssue, HookResult, WritingHooksEngine

__all__ = [
    "CheckpointManager",
    "ConstraintCategory",
    "ConstraintViolation",
    "DataArtifactTracker",
    "DomainConstraintEngine",
    "DraftSnapshotManager",
    "EvolutionVerifier",
    "FileStorage",
    "GateResult",
    "HookEffectivenessTracker",
    "HookIssue",
    "HookResult",
    "MetaLearningEngine",
    "PipelineGateValidator",
    "ProjectManager",
    "ProjectMemoryManager",
    "ProjectRepository",
    "QualityScorecard",
    "ReferenceManager",
    "ReferenceRepository",
    "WorkspaceStateManager",
    "WritingHooksEngine",
    "get_project_manager",
    "get_workspace_state_manager",
    "reset_workspace_state_manager",
]
