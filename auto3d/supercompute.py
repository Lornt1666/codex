"""Supercomputing blueprint helpers for the Auto3D toolkit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SupercomputeLayer:
    """Single layer in the supercomputing automation stack."""

    key: str
    label: str
    objective: str
    ai_capabilities: tuple[str, ...]
    infrastructure: tuple[str, ...]
    deliverables: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:  # pragma: no cover - trivial wrapper
        return asdict(self)


@dataclass(frozen=True)
class SupercomputeBlueprint:
    """Mission statement and layered plan for Auto3D supercomputing."""

    protocol: str
    mission: str
    layers: tuple[SupercomputeLayer, ...]
    orchestration: tuple[str, ...]
    telemetry: tuple[str, ...]
    differentiators: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:  # pragma: no cover - trivial wrapper
        return asdict(self)


@dataclass(frozen=True)
class SupercomputeReadiness:
    """Assessment of how close the user is to the supercomputing blueprint."""

    blueprint: SupercomputeBlueprint
    required_capabilities: tuple[str, ...]
    available_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:  # pragma: no cover - trivial wrapper
        payload = asdict(self)
        payload["blueprint"] = self.blueprint.to_dict()
        return payload


SUPERCOMPUTE_REQUIRED_CAPABILITIES: tuple[str, ...] = (
    "tripo_sr_single_image",
    "controlnet_view_synthesis",
    "meshroom_photogrammetry",
    "nerfstudio_gaussian",
    "geonodes_parametric",
    "freecad_brep_conversion",
    "meshfix_print_prep",
    "material_diffusion_baking",
    "distributed_hpc_orchestration",
)


def supercompute_blueprint(*, protocol: str) -> SupercomputeBlueprint:
    """Return the canonical 1JGM∞.BE supercomputing blueprint."""

    layers = (
        SupercomputeLayer(
            key="ingestion",
            label="Ingestion & Vision",
            objective=(
                "Capture hero renders and synthesise missing perspectives so every facade feeds the pipeline."
            ),
            ai_capabilities=("tripo_sr_single_image", "controlnet_view_synthesis"),
            infrastructure=(
                "GPU workstations",
                "Prompt trace logging",
                "Asset provenance register",
            ),
            deliverables=(
                "Curated hero render vault",
                "Synthetic multi-view packs",
                "Prompt lineage reports",
            ),
        ),
        SupercomputeLayer(
            key="reconstruction",
            label="Reconstruction & Massing",
            objective=(
                "Convert view packs into watertight meshes, wing/dormer massing, and catalogue-ready geometries."
            ),
            ai_capabilities=(
                "meshroom_photogrammetry",
                "nerfstudio_gaussian",
                "geonodes_parametric",
            ),
            infrastructure=(
                "Photogrammetry farm",
                "Parametric geometry node library",
                "Asset quality dashboards",
            ),
            deliverables=(
                "Textured meshes",
                "Parametric catalog variants",
                "Telemetry snapshots",
            ),
        ),
        SupercomputeLayer(
            key="conversion",
            label="Conversion & Print Prep",
            objective=(
                "Translate meshes into CAD solids, ensure watertight slices, and archive annotated STL stacks."
            ),
            ai_capabilities=(
                "freecad_brep_conversion",
                "meshfix_print_prep",
                "material_diffusion_baking",
            ),
            infrastructure=(
                "B-Rep processing nodes",
                "3D print QA lab",
                "Material/texture baking queue",
            ),
            deliverables=(
                "STEP/BREP dossiers",
                "Floor-by-floor STL bundles",
                "Look-dev reference atlases",
            ),
        ),
        SupercomputeLayer(
            key="orchestration",
            label="Orchestration & Scaling",
            objective=(
                "Schedule AI + CAD workloads across HPC clusters so every render-to-print request stays on rails."
            ),
            ai_capabilities=("distributed_hpc_orchestration",),
            infrastructure=(
                "Hybrid HPC/cloud queue",
                "Policy-aware job scheduler",
                "Cost + carbon telemetry",
            ),
            deliverables=(
                "Execution manifests",
                "SLA compliance reports",
                "Energy + runtime dashboards",
            ),
        ),
    )

    return SupercomputeBlueprint(
        protocol=protocol,
        mission=(
            "Coordinate the Auto3D pipeline as an artificial supercomputing intelligence for Justice Gray Maciocha's multi-alias studios."
        ),
        layers=layers,
        orchestration=(
            "Single prompt → multi-view synthesis → photogrammetry → STL slicing",
            "Continuous verification with Auto3D quality gates",
            "Bundle outputs for marketplaces, real estate previews, and educational kits",
        ),
        telemetry=(
            "Square-footage lineage from metres to millimetres",
            "AI capability provenance",
            "Regulation + permit tracebacks",
        ),
        differentiators=(
            "Protocol 1JGM∞.BE compliance",
            "Alias-aware branding (Justice Gray Maciocha, Satoshi _amamoto, Lornt)",
            "Toy-scale reliability with supercomputing ambition",
        ),
    )


def evaluate_supercompute(
    *,
    available_capabilities: Sequence[str] | None = None,
    protocol: str,
) -> SupercomputeReadiness:
    """Return readiness information for the requested protocol."""

    blueprint = supercompute_blueprint(protocol=protocol)
    available = _unique_ordered(available_capabilities or ())
    available_set = set(available)
    missing = tuple(key for key in SUPERCOMPUTE_REQUIRED_CAPABILITIES if key not in available_set)

    recommended: list[str] = []
    if "distributed_hpc_orchestration" in missing:
        recommended.append(
            "Integrate an HPC scheduler (Slurm, Azure Batch, AWS Batch) to queue multi-stage Auto3D jobs."
        )
    if "meshroom_photogrammetry" in missing or "nerfstudio_gaussian" in missing:
        recommended.append(
            "Augment single-image meshes with photogrammetry or gaussian splats for catalogue-quality backsides."
        )
    if "freecad_brep_conversion" in missing:
        recommended.append(
            "Adopt a mesh-to-BREP bridge (FreeCAD/Open Cascade) so CAD-grade solids stay in lockstep with STL slices."
        )
    if "material_diffusion_baking" in missing:
        recommended.append("Bake presentation textures to pair prints with photoreal marketing renders.")

    notes = (
        "Mark capabilities as available with --capability flags or in your Codex prompt to refine the readiness output.",
        "Required capabilities map to the AI catalog so you can script upgrades over time.",
    )

    return SupercomputeReadiness(
        blueprint=blueprint,
        required_capabilities=SUPERCOMPUTE_REQUIRED_CAPABILITIES,
        available_capabilities=available,
        missing_capabilities=missing,
        recommended_actions=tuple(recommended) if recommended else (
            "All required capabilities are present. Scale monitoring and resilience next.",
        ),
        notes=notes,
    )


def _unique_ordered(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return tuple(ordered)
