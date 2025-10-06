"""Curated catalog of AI-assisted 3D generation capabilities."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class AICapability:
    """Description of a single AI or computational design capability."""

    key: str
    label: str
    category: str
    description: str
    inputs: list[str]
    outputs: list[str]
    providers: list[str]
    offline_ready: bool
    notes: list[str]

    def to_dict(self) -> dict[str, object]:  # pragma: no cover - trivial wrapper
        return asdict(self)


_CATALOG: list[AICapability] = [
    AICapability(
        key="tripo_sr_single_image",
        label="TripoSR single-image reconstruction",
        category="Reconstruction",
        description=(
            "VAST's TripoSR quickly turns a single hero render into a watertight mesh, "
            "making it the fastest on-ramp from 2D concept art to printable geometry."
        ),
        inputs=["Single hero render"],
        outputs=["OBJ/GLB mesh"],
        providers=["VAST-AI Research", "GitHub"],
        offline_ready=True,
        notes=[
            "Runs locally on consumer GPUs (CUDA) or CPU with longer runtimes.",
            "Works best with three-quarter views where two façades are visible.",
        ],
    ),
    AICapability(
        key="controlnet_view_synthesis",
        label="ControlNet view synthesis",
        category="Generative augmentation",
        description=(
            "ControlNet + diffusion models hallucinate matching side, rear, and roof views "
            "from a single prompt, feeding downstream photogrammetry or gaussian splatting."
        ),
        inputs=["Prompt", "Reference hero render"],
        outputs=["Synthetically matched view set"],
        providers=["Automatic1111", "ComfyUI", "InvokeAI"],
        offline_ready=True,
        notes=[
            "Pair with depth or normal maps for better structural fidelity.",
            "Use small prompt tweaks (e.g., \"same proportions\") to keep features aligned.",
        ],
    ),
    AICapability(
        key="meshroom_photogrammetry",
        label="Meshroom / COLMAP photogrammetry",
        category="Photogrammetry",
        description=(
            "Multi-view reconstruction pipelines convert real or synthetic views into "
            "detailed textured meshes with strong wall alignment and roof accuracy."
        ),
        inputs=["6-20 calibrated renders"],
        outputs=["Textured mesh", "Camera bundle"],
        providers=["AliceVision Meshroom", "COLMAP", "OpenMVS"],
        offline_ready=True,
        notes=[
            "Great for catalog-quality façades once you can supply consistent views.",
            "Exports mesh + cameras for reuse in Blender or slicers.",
        ],
    ),
    AICapability(
        key="nerfstudio_gaussian",
        label="Nerfstudio gaussian splatting",
        category="Radiance fields",
        description=(
            "Gaussian splatting via Nerfstudio or Splatfacto yields light-weight point-based "
            "representations that render in real time and back-project to meshes."
        ),
        inputs=["Short camera sweep", "Synthetic or captured views"],
        outputs=["Gaussian point cloud", "Optional mesh"],
        providers=["Nerfstudio", "Splatfacto", "Luma"],
        offline_ready=False,
        notes=[
            "Excellent for quick previews before committing to heavy meshing.",
            "Export splats to OBJ/PLY for combination with STL slicing heuristics.",
        ],
    ),
    AICapability(
        key="geonodes_parametric",
        label="Blender Geometry Nodes massing",
        category="Procedural design",
        description=(
            "Geometry Nodes graphs parameterise wings, dormers, porches, and roofs, letting "
            "you iterate through catalog variants driven by prompt-derived dimensions."
        ),
        inputs=["Prompt metrics", "Node graph parameters"],
        outputs=["Parametric Blender scene", "Batch exportable STLs"],
        providers=["Blender"],
        offline_ready=True,
        notes=[
            "Bake variants to GLB/STL once satisfied with the configuration.",
            "Combine with Auto3D catalog outputs for procedural overbuilds.",
        ],
    ),
    AICapability(
        key="freecad_brep_conversion",
        label="FreeCAD mesh-to-BREP conversion",
        category="CAD conversion",
        description=(
            "FreeCAD and Open Cascade toolchains convert triangulated meshes into CAD solids, "
            "unlocking precise section cuts, annotations, and CNC-friendly exports."
        ),
        inputs=["Watertight mesh"],
        outputs=["STEP", "IGES", "BREP"],
        providers=["FreeCAD", "Open Cascade"],
        offline_ready=True,
        notes=[
            "Use on catalog variants that need parametric downstream edits.",
            "Combine with slicer heuristics to keep floors watertight post-conversion.",
        ],
    ),
    AICapability(
        key="meshfix_print_prep",
        label="MeshFix / Blender 3D Print Toolbox",
        category="Print preparation",
        description=(
            "Mesh repair utilities close holes, decimate noise, and enforce manifold shells so "
            "floor-by-floor STLs stay reliable on FDM and resin printers."
        ),
        inputs=["Triangulated mesh"],
        outputs=["Watertight STL"],
        providers=["MeshFix", "Blender 3D Print Toolbox", "meshlabserver"],
        offline_ready=True,
        notes=[
            "Run before handing geometry to Auto3D slicing helpers.",
            "Automate via Blender Python or Meshlab scripts for batch cleanup.",
        ],
    ),
    AICapability(
        key="material_diffusion_baking",
        label="Material diffusion + texture baking",
        category="Look development",
        description=(
            "Material diffusion models (e.g., Material Diffusion, Adobe Firefly) synthesise "
            "plausible texture sets that can be baked into STL previews or marketing renders."
        ),
        inputs=["Prompt", "Ambient occlusion", "Curvature maps"],
        outputs=["PBR texture sets", "Reference renders"],
        providers=["Stability AI", "Adobe Firefly", "Hugging Face"],
        offline_ready=False,
        notes=[
            "Helpful for catalog boards even when the printed model remains monochrome.",
            "Export atlases alongside STL metadata for presentation packages.",
        ],
    ),
    AICapability(
        key="distributed_hpc_orchestration",
        label="Distributed HPC orchestration",
        category="Supercomputing coordination",
        description=(
            "Hybrid HPC and cloud schedulers (Slurm, Azure Batch, AWS Batch) queue Auto3D's "
            "multi-stage jobs so renders, photogrammetry, and slicing scale without manual intervention."
        ),
        inputs=["Capability manifest", "Mesh/STL job queue"],
        outputs=["Execution manifests", "Telemetry streams"],
        providers=["Slurm", "Azure Batch", "AWS Batch", "Kubernetes"],
        offline_ready=False,
        notes=[
            "Pin workflows to GPU or CPU pools depending on stage (TripoSR vs. slicer).",
            "Feed telemetry back into the Auto3D reports so clients see runtimes and energy usage.",
        ],
    ),
]


_KEY_TO_CAPABILITY = {cap.key: cap for cap in _CATALOG}


def capability_catalog() -> list[AICapability]:
    """Return the full, ordered AI capability catalog."""

    return list(_CATALOG)


def _extend_unique(target: list[AICapability], keys: Iterable[str]) -> None:
    seen = {cap.key for cap in target}
    for key in keys:
        cap = _KEY_TO_CAPABILITY.get(key)
        if cap and cap.key not in seen:
            target.append(cap)
            seen.add(cap.key)


def recommended_capabilities(
    *,
    style_tags: Sequence[str] | None = None,
    floors: int | None = None,
    has_basement: bool | None = None,
    include_catalog_overview: bool = True,
) -> list[AICapability]:
    """Suggest a stack of capabilities tailored to the parsed prompt."""

    tags = {tag.lower() for tag in (style_tags or [])}
    result: list[AICapability] = []

    core = ["tripo_sr_single_image", "meshfix_print_prep"]
    _extend_unique(result, core)

    # Photogrammetry becomes more valuable for taller or more articulated programmes.
    if floors and floors >= 2:
        _extend_unique(result, ["meshroom_photogrammetry"])
    if floors and floors >= 3:
        _extend_unique(result, ["nerfstudio_gaussian"])

    if has_basement:
        _extend_unique(result, ["freecad_brep_conversion"])

    # Style-driven suggestions.
    if tags & {"scandinavian", "dutch"}:
        _extend_unique(result, ["geonodes_parametric"])
    if tags & {"irish", "scottish"}:
        _extend_unique(result, ["controlnet_view_synthesis"])
    if tags & {"canadian", "american"}:
        _extend_unique(result, ["material_diffusion_baking"])

    if include_catalog_overview:
        _extend_unique(result, ["controlnet_view_synthesis"])

    # Supercomputing orchestration is the backbone for 1JGM∞.BE automation.
    _extend_unique(result, ["distributed_hpc_orchestration"])

    return result


__all__ = ["AICapability", "capability_catalog", "recommended_capabilities"]
