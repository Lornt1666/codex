"""Static site generator for the Auto3D application experience."""
from __future__ import annotations

import functools
import threading
from dataclasses import dataclass
from pathlib import Path
import shutil
import textwrap
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable, Sequence

from .automation import automation_guidelines
from .capabilities import AICapability
from .regulations import BuildingCodeReference, building_code_catalog
from .supercompute import SupercomputeReadiness


ThreadingHTTPServer.allow_reuse_address = True

REPO_ROOT = Path(__file__).resolve().parent.parent


def _format_host_for_url(host: str) -> str:
    """Return *host* wrapped for inclusion in an HTTP URL."""

    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


@dataclass
class SiteServer:
    """Information about a running preview server for the static site."""

    directory: Path
    host: str
    port: int
    url: str
    _server: ThreadingHTTPServer
    _thread: threading.Thread

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)

    def stop(self) -> None:
        """Shut down the preview server."""

        if not self._thread.is_alive():
            self._server.server_close()
            return

        self._server.shutdown()
        self._thread.join(timeout=2.0)
        self._server.server_close()


def start_site_server(
    directory: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> SiteServer:
    """Launch a background HTTP server that serves *directory* and return its info."""

    directory = directory.expanduser().resolve()
    if not directory.exists():
        raise FileNotFoundError(f"Site directory does not exist: {directory}")

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    actual_port = server.server_address[1]
    display_host = _format_host_for_url(host)
    url = f"http://{display_host}:{actual_port}/"

    thread = threading.Thread(
        target=server.serve_forever,
        name="Auto3DSiteServer",
        daemon=True,
    )
    thread.start()

    return SiteServer(
        directory=directory,
        host=display_host,
        port=actual_port,
        url=url,
        _server=server,
        _thread=thread,
    )


@dataclass(frozen=True)
class SiteFeature:
    """Representation of a feature section on the marketing site."""

    route: str
    title: str
    description: str


@dataclass(frozen=True)
class PipelineStep:
    """Representation of an in-app pipeline step for display."""

    title: str
    summary: str
    actions: list[str]


TOP_LEVEL_FEATURES: tuple[SiteFeature, ...] = (
    SiteFeature(
        route="/home",
        title="Mission Control",
        description=(
            "Launch your Auto3D runs, reopen past house studies, and jump straight "
            "into the help centre with one click."
        ),
    ),
    SiteFeature(
        route="/projects",
        title="Project Manager",
        description=(
            "Organise hero renders, meshes, slicing configs, and reports per build "
            "so every iteration stays reproducible."
        ),
    ),
    SiteFeature(
        route="/upload",
        title="Render Uploads",
        description=(
            "Drag hero renders, synthetic view sets, or catalog prompts into the "
            "pipeline drop zone with verification previews."
        ),
    ),
    SiteFeature(
        route="/convert",
        title="Image → 3D Converter",
        description=(
            "Feed TripoSR or Meshroom directly from the browser to obtain clean "
            "watertight meshes for printing."
        ),
    ),
    SiteFeature(
        route="/cleanup",
        title="Mesh Cleanup",
        description=(
            "Apply the Blender macro, floor snapping, and solidify routines without "
            "leaving the orchestration app."
        ),
    ),
    SiteFeature(
        route="/slice",
        title="Floor Slicer",
        description=(
            "Tune storey heights interactively and export per-floor STLs as soon as "
            "the geometry validates."
        ),
    ),
    SiteFeature(
        route="/preview",
        title="Exploded Preview",
        description=(
            "Inspect exploded views, rescale models to centimetres or millimetres, "
            "and review structural call-outs before print."
        ),
    ),
    SiteFeature(
        route="/supercompute",
        title="Supercomputing Blueprint",
        description=(
            "Map ingestion, reconstruction, conversion, and orchestration layers "
            "to the 1JGM∞.BE protocol with readiness checks."
        ),
    ),
    SiteFeature(
        route="/download",
        title="Download Centre",
        description=(
            "Grab floor stacks, assembled STLs, YAML configs, and presentation GLBs "
            "in a single bundle."
        ),
    ),
    SiteFeature(
        route="/automation",
        title="Automation Hub",
        description=(
            "Generate Playwright upload scripts, validate selectors, and sync marketplace listings."
        ),
    ),
    SiteFeature(
        route="/regulations",
        title="Regulation Atlas",
        description=(
            "Reference Alberta, Canadian, and continental building codes with STL-friendly notes."
        ),
    ),
    SiteFeature(
        route="/settings",
        title="Global Settings",
        description=(
            "Lock in preferred units, tolerances, and output directories for "
            "every future project."
        ),
    ),
    SiteFeature(
        route="/help",
        title="Help & Protocols",
        description=(
            "Surface onboarding clips, protocol 1JGM∞.BE guidelines, and contact "
            "routes under a single support roof."
        ),
    ),
)


PIPELINE_STEPS: tuple[PipelineStep, ...] = (
    PipelineStep(
        title="Upload Image(s)",
        summary="Drag hero renders or generated view sets into the pipeline.",
        actions=[
            "Drop ChatGPT renders or ControlNet variants into the dropzone.",
            "Reorder or remove shots before reconstruction.",
            "Tag captures with region, storey count, and programme.",
        ],
    ),
    PipelineStep(
        title="Generate Base Mesh",
        summary="Run TripoSR or Meshroom headlessly with progress telemetry.",
        actions=[
            "Select single-image TripoSR for speed or Meshroom for fidelity.",
            "Monitor reconstruction logs and estimated remaining time.",
            "Archive raw outputs into the project working folder automatically.",
        ],
    ),
    PipelineStep(
        title="Clean & Repair",
        summary="Trigger the Blender macro for floor snapping and wall solidification.",
        actions=[
            "Merge duplicate vertices and close open façades in one pass.",
            "Snap floor plates to centimetre-aligned planes with tolerance controls.",
            "Apply print-ready wall thickness heuristics for toy-scale models.",
        ],
    ),
    PipelineStep(
        title="Slice Floors",
        summary="Preview storey bands and export watertight STLs per level.",
        actions=[
            "Edit YAML breakpoints or use interactive sliders to tune heights.",
            "Preview slice planes before committing to exports.",
            "Emit optional roof segments and assembled stacks for packaging.",
        ],
    ),
    PipelineStep(
        title="Printability Gate",
        summary="Verify shell thickness, footprint, and stack height before download.",
        actions=[
            "Automated checks enforce >0.6 mm shells and healthy footprints.",
            "Failures block exports and surface remediation tips in printability.md.",
            "Use recommendations to pick slicer orientation and adhesion strategies.",
        ],
    ),
    PipelineStep(
        title="Preview & Scale",
        summary="Inspect exploded views, measure spans, and set final scale ratios.",
        actions=[
            "Switch between 1:50, 1:100, and custom centimetre / millimetre scales.",
            "Validate overhangs and bridging spans with integrated print checks.",
            "Capture turntable renders for catalog sharing.",
        ],
    ),
    PipelineStep(
        title="Download & Deploy",
        summary="Bundle STLs, configs, and reports for immediate fabrication.",
        actions=[
            "Download per-floor STLs, assembled stacks, and protocol reports.",
            "Queue direct hand-off to Cura, PrusaSlicer, or Bambu Studio.",
            "Sync catalog variants back to the Auto3D workspace archive.",
        ],
    ),
)


GALLERY_IMAGES: tuple[tuple[str, str], ...] = (
    ("supercomputing.svg", "Supercomputing intelligence gradients celebrating Justice Gray Maciocha"),
    ("catalog.svg", "Catalog orchestration for Satoshi _amamoto variants"),
    ("stl.svg", "Lornt protocol-driven STL engineering"),
)


def _write_file(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def _render_features_html(features: Iterable[SiteFeature]) -> str:
    blocks: list[str] = []
    for feature in features:
        blocks.append(
            textwrap.dedent(
                f"""
                <article class=\"feature-card\" id=\"{feature.route[1:]}\">
                    <h3>{feature.title}</h3>
                    <p>{feature.description}</p>
                    <a class=\"route-link\" href=\"{feature.route}\">Go to {feature.route}</a>
                </article>
                """
            ).strip()
        )
    return "\n".join(blocks)


def _render_pipeline_html(steps: Iterable[PipelineStep]) -> str:
    items: list[str] = []
    for step in steps:
        actions = "".join(f"<li>{action}</li>" for action in step.actions)
        items.append(
            textwrap.dedent(
                f"""
                <article class=\"pipeline-step\">
                    <header>
                        <h3>{step.title}</h3>
                        <p>{step.summary}</p>
                    </header>
                    <ul>{actions}</ul>
                </article>
                """
            ).strip()
        )
    return "\n".join(items)


def _render_capabilities_html(capabilities: Sequence[AICapability]) -> str:
    cards: list[str] = []
    for capability in capabilities:
        inputs = "".join(f"<li>{item}</li>" for item in capability.inputs)
        outputs = "".join(f"<li>{item}</li>" for item in capability.outputs)
        providers = "".join(f"<li>{item}</li>" for item in capability.providers)
        notes = "".join(f"<li>{item}</li>" for item in capability.notes)
        cards.append(
            textwrap.dedent(
                f"""
                <article class=\"capability-card\" data-category=\"{capability.category}\">
                    <h3>{capability.label}</h3>
                    <p class=\"category\">{capability.category}</p>
                    <p>{capability.description}</p>
                    <section>
                        <h4>Inputs</h4>
                        <ul>{inputs}</ul>
                    </section>
                    <section>
                        <h4>Outputs</h4>
                        <ul>{outputs}</ul>
                    </section>
                    <section>
                        <h4>Providers</h4>
                        <ul>{providers}</ul>
                    </section>
                    <section>
                        <h4>Notes</h4>
                        <ul>{notes}</ul>
                    </section>
                    <p class=\"offline\">Offline Ready: {"Yes" if capability.offline_ready else "Remote"}</p>
                </article>
                """
            ).strip()
        )
    return "\n".join(cards)


def _render_supercompute_html(
    readiness: SupercomputeReadiness,
    available_caps: Sequence[AICapability],
    missing_caps: Sequence[AICapability],
    capability_lookup: dict[str, AICapability],
) -> str:
    layers: list[str] = []
    for layer in readiness.blueprint.layers:
        capability_labels = []
        for key in layer.ai_capabilities:
            capability = capability_lookup.get(key)
            capability_labels.append(capability.label if capability else key)
        labels = ", ".join(capability_labels)
        infrastructure = ", ".join(layer.infrastructure)
        deliverables = ", ".join(layer.deliverables)
        layers.append(
            textwrap.dedent(
                f"""
                <article class=\"supercompute-layer\">
                    <h3>{layer.label}</h3>
                    <p>{layer.objective}</p>
                    <ul>
                        <li><strong>AI stack:</strong> {labels}</li>
                        <li><strong>Infrastructure:</strong> {infrastructure}</li>
                        <li><strong>Deliverables:</strong> {deliverables}</li>
                    </ul>
                </article>
                """
            ).strip()
        )

    def _format_caps(items: Sequence[AICapability]) -> str:
        if not items:
            return "<p class=\"empty\">None</p>"
        entries = "".join(
            f"<li><strong>{cap.label}</strong> <span class=\"dim\">({cap.key})</span></li>"
            for cap in items
        )
        return f"<ul class=\"capability-list\">{entries}</ul>"

    actions = "".join(f"<li>{action}</li>" for action in readiness.recommended_actions)
    notes = "".join(f"<li>{note}</li>" for note in readiness.notes)

    overview = textwrap.dedent(
        """
        <article class=\"supercompute-overview\">
            <h3>Mission Control</h3>
            <p>{mission}</p>
            <h4>Orchestration Pathways</h4>
            <ul>{orchestration}</ul>
            <h4>Telemetry Channels</h4>
            <ul>{telemetry}</ul>
            <h4>Differentiators</h4>
            <ul>{differentiators}</ul>
        </article>
        """
    ).strip().format(
        mission=readiness.blueprint.mission,
        orchestration="".join(f"<li>{item}</li>" for item in readiness.blueprint.orchestration),
        telemetry="".join(f"<li>{item}</li>" for item in readiness.blueprint.telemetry),
        differentiators="".join(f"<li>{item}</li>" for item in readiness.blueprint.differentiators),
    )

    status = textwrap.dedent(
        """
        <article class=\"supercompute-status\">
            <h3>Capability Readiness</h3>
            <h4>Available</h4>
            {available}
            <h4>Missing</h4>
            {missing}
            <h4>Recommended Actions</h4>
            <ul class=\"action-list\">{actions}</ul>
            <h4>Notes</h4>
            <ul class=\"note-list\">{notes}</ul>
        </article>
        """
    ).strip().format(
        available=_format_caps(tuple(available_caps)),
        missing=_format_caps(tuple(missing_caps)),
        actions=actions,
        notes=notes,
    )

    return "".join(
        [
            "<div class=\"supercompute-grid\">",
            overview,
            f"<div class=\"supercompute-layers\">{''.join(layers)}</div>",
            status,
            "</div>",
        ]
    )


def _render_automation_html(tips: Sequence[str]) -> str:
    steps = "".join(f"<li>{tip}</li>" for tip in tips)
    command = (
        "python -m auto3d --workspace Auto3D-Render-to-STL automation "
        "--url https://seller.example.com/upload --upload-path Auto3D-Render-to-STL/outputs/assembled.stl"
    )
    return textwrap.dedent(
        f"""
        <article class=\"automation-card\">
            <header>
                <h3>Generate Your Upload Script</h3>
                <p>Use the automation command to scaffold a Playwright runner for marketplace uploads.</p>
            </header>
            <pre><code>{command}</code></pre>
            <h4>Operational Guardrails</h4>
            <ul class=\"automation-steps\">{steps}</ul>
        </article>
        """
    ).strip()


def _render_regulations_html(references: Sequence[BuildingCodeReference]) -> str:
    cards: list[str] = []
    for reference in references:
        notes = "".join(f"<li>{note}</li>" for note in reference.notes)
        scales = ", ".join(reference.scale_applicability)
        cards.append(
            textwrap.dedent(
                f"""
                <article class=\"regulation-card\" data-region=\"{reference.region}\">
                    <header>
                        <h3>{reference.name}</h3>
                        <p class=\"jurisdiction\">{reference.jurisdiction} · {reference.region.title()}</p>
                    </header>
                    <p>{reference.description}</p>
                    <p class=\"scale\">Applies to: {scales}</p>
                    <p><a href=\"{reference.url}\">Official reference</a></p>
                    <ul>{notes}</ul>
                </article>
                """
            ).strip()
        )
    return "\n".join(cards)


def _write_gallery_assets(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    palette = [
        ("supercomputing.svg", "#0b1026", "#2c55ff", "Supercomputing AI Grid"),
        ("catalog.svg", "#140a1d", "#ff7ad9", "Catalog Variants"),
        ("stl.svg", "#121212", "#f5b200", "Protocol 1JGM∞.BE"),
    ]
    template = textwrap.dedent(
        """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 200'>
          <defs>
            <linearGradient id='grad' x1='0' y1='0' x2='1' y2='1'>
              <stop offset='0%' stop-color='{start}' />
              <stop offset='100%' stop-color='{end}' />
            </linearGradient>
          </defs>
          <rect width='320' height='200' fill='url(#grad)' rx='24' />
          <g fill='white' font-family='"Fira Sans", "Segoe UI", sans-serif'>
            <text x='24' y='72' font-size='28' font-weight='700'>{headline}</text>
            <text x='24' y='116' font-size='18' opacity='0.9'>Justice Gray Maciocha • Satoshi _amamoto • Lornt</text>
            <text x='24' y='148' font-size='16' opacity='0.75'>Supercomputing Artificial Intelligence</text>
          </g>
          <g stroke='rgba(255,255,255,0.35)' stroke-width='0.75'>
            <path d='M40 30h240M40 70h240M40 110h240M40 150h240' />
            <path d='M40 30v140M120 30v140M200 30v140M280 30v140' />
          </g>
        </svg>
        """
    )
    for name, start, end, headline in palette:
        _write_file(directory / name, template.format(start=start, end=end, headline=headline))


def _render_gallery_html(images: Sequence[tuple[str, str]]) -> str:
    return "\n".join(
        textwrap.dedent(
            f"""
            <figure class=\"gallery-card\">
                <img src=\"assets/{filename}\" alt=\"{alt}\" loading=\"lazy\" />
                <figcaption>{alt}</figcaption>
            </figure>
            """
        ).strip()
        for filename, alt in images
    )


def _build_html_document(
    *,
    protocol: str,
    features_html: str,
    pipeline_html: str,
    supercompute_html: str,
    automation_html: str,
    regulations_html: str,
    capabilities_html: str,
    gallery_html: str,
    download_href: str,
    download_enabled: bool,
) -> str:
    secondary_class = "disabled" if not download_enabled else ""
    download_attr = "download=\"auto3d-application.zip\"" if download_enabled else ""
    hint = (
        '<p class="hint">Run <code>python -m auto3d web --output auto3d_site --force</code> '
        "to regenerate this bundle.</p>"
        if download_enabled
        else '<p class="hint">Run <code>python -m auto3d web --output auto3d_site --force</code> '
        "to generate the downloadable bundle locally.</p>"
    )

    return textwrap.dedent(
        f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
            <meta charset=\"utf-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
            <title>Auto3D Mission Control · Protocol {protocol}</title>
            <link rel=\"stylesheet\" href=\"styles.css\" />
            <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
            <link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;500;600;700&display=swap\" />
        </head>
        <body>
            <header class=\"hero\">
                <div class=\"hero-content\">
                    <p class=\"protocol\">Protocol {protocol}</p>
                    <h1>Auto3D Mission Control</h1>
                    <p class=\"tagline\">Justice Gray Maciocha · Satoshi _amamoto · Lornt — Supercomputing grade automation for STL-ready house maquettes.</p>
                    <div class=\"hero-actions\">
                        <a class=\"primary\" href=\"#features\">Explore the platform</a>
                        <a class=\"secondary {secondary_class}\" href=\"{download_href}\" {download_attr}>Download Auto3D Suite</a>
                    </div>
                </div>
                <div class=\"hero-grid\" aria-hidden=\"true\"></div>
            </header>
            <main>
                <section id=\"features\" class=\"section features\">
                    <h2>Route the Experience</h2>
                    <div class=\"feature-grid\">{features_html}</div>
                </section>
                <section id=\"pipeline\" class=\"section pipeline\">
                    <h2>Pipeline Control Deck</h2>
                    <div class=\"pipeline-grid\">{pipeline_html}</div>
                </section>
                <section id=\"supercompute\" class=\"section supercompute\">
                    <h2>Supercomputing Blueprint</h2>
                    {supercompute_html}
                </section>
                <section id=\"automation\" class=\"section automation\">
                    <h2>Automation Playbook</h2>
                    {automation_html}
                </section>
                <section id=\"gallery\" class=\"section gallery\">
                    <h2>Supercomputing Visuals</h2>
                    <div class=\"gallery-grid\">{gallery_html}</div>
                </section>
                <section id=\"regulations\" class=\"section regulations\">
                    <h2>Regulation Atlas</h2>
                    <div class=\"regulation-grid\">{regulations_html}</div>
                </section>
                <section id=\"capabilities\" class=\"section capabilities\">
                    <h2>Artificial Intelligence Stack</h2>
                    <p class=\"section-lead\">Curated AI assists for 1JGM∞.BE — offline-first when you need to stay local.</p>
                    <div class=\"capability-grid\">{capabilities_html}</div>
                </section>
                <section id=\"download\" class=\"section download\">
                    <h2>Download the Suite</h2>
                    <p>Ready to print? Grab the CLI, wizards, and docs bundled for Justice Gray Maciocha's Auto3D studios.</p>
                    <a class=\"primary {secondary_class}\" href=\"{download_href}\" {download_attr}>Download Auto3D Suite</a>
                    {hint}
                </section>
            </main>
            <footer class=\"footer\">
                <p>&copy; {protocol} Justice Gray Maciocha · Satoshi _amamoto · Lornt. Engineered with Auto3D and 1JGM∞.BE protocols.</p>
            </footer>
            <script src=\"script.js\"></script>
        </body>
        </html>
        """
    ).strip()


CSS_STYLES = textwrap.dedent(
    """
    :root {
        color-scheme: dark;
        font-family: 'Fira Sans', 'Segoe UI', sans-serif;
        background-color: #05030f;
        color: #f8f9ff;
        --accent: #6c7bff;
        --accent-secondary: #ff9bcf;
        --card: rgba(16, 20, 48, 0.65);
        --card-border: rgba(255, 255, 255, 0.08);
        --shadow: 0 24px 60px rgba(12, 20, 56, 0.35);
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        line-height: 1.6;
        background-image: radial-gradient(circle at 20% 20%, rgba(50, 60, 160, 0.45), transparent 55%),
            radial-gradient(circle at 80% 10%, rgba(255, 140, 190, 0.35), transparent 55%),
            linear-gradient(180deg, rgba(5, 3, 15, 0.95), rgba(5, 3, 15, 0.98));
        min-height: 100vh;
    }

    h1, h2, h3, h4 {
        margin-top: 0;
    }

    a {
        color: inherit;
    }

    .hero {
        position: relative;
        padding: 6rem clamp(1.5rem, 6vw, 6rem) 5rem;
        overflow: hidden;
    }

    .hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 20% 20%, rgba(108, 123, 255, 0.35), transparent 60%),
            radial-gradient(circle at 70% 30%, rgba(255, 155, 207, 0.3), transparent 65%);
        filter: blur(32px);
        z-index: 0;
    }

    .hero-content {
        position: relative;
        z-index: 2;
        max-width: 760px;
    }

    .hero-grid {
        position: absolute;
        inset: 0;
        background-image: linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
        background-size: 80px 80px;
        opacity: 0.4;
        z-index: 1;
    }

    .protocol {
        text-transform: uppercase;
        letter-spacing: 0.4em;
        font-size: 0.75rem;
        color: rgba(248, 249, 255, 0.7);
    }

    .tagline {
        font-size: clamp(1rem, 2.4vw, 1.25rem);
        color: rgba(248, 249, 255, 0.8);
    }

    .hero-actions {
        margin-top: 2.5rem;
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .primary,
    .secondary {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.85rem 1.6rem;
        border-radius: 999px;
        text-decoration: none;
        font-weight: 600;
        transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
    }

    .primary {
        background: linear-gradient(120deg, var(--accent), var(--accent-secondary));
        color: #05030f;
        box-shadow: var(--shadow);
    }

    .secondary {
        border: 1px solid rgba(248, 249, 255, 0.3);
        background: rgba(6, 6, 18, 0.65);
        color: #f8f9ff;
    }

    .primary:hover,
    .secondary:hover {
        transform: translateY(-2px);
    }

    .secondary.disabled,
    .primary.disabled {
        opacity: 0.5;
        pointer-events: none;
    }

    .section {
        padding: clamp(3.5rem, 6vw, 6rem) clamp(1.5rem, 6vw, 6rem);
    }

    .section h2 {
        font-size: clamp(2rem, 3vw, 2.5rem);
        margin-bottom: 1.5rem;
    }

    .section-lead {
        max-width: 640px;
        color: rgba(248, 249, 255, 0.75);
    }

    .feature-grid,
    .pipeline-grid,
    .capability-grid,
    .gallery-grid,
    .regulation-grid {
        display: grid;
        gap: clamp(1.25rem, 2vw, 2rem);
    }

    .feature-grid {
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }

    .feature-card,
    .pipeline-step,
    .capability-card,
    .gallery-card,
    .automation-card,
    .regulation-card {
        background: var(--card);
        border: 1px solid var(--card-border);
        border-radius: 24px;
        padding: 1.75rem;
        backdrop-filter: blur(16px);
        box-shadow: var(--shadow);
    }

    .feature-card h3,
    .pipeline-step h3,
    .capability-card h3 {
        font-size: 1.35rem;
    }

    .route-link {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
        color: rgba(248, 249, 255, 0.8);
        text-decoration: none;
        font-weight: 500;
    }

    .pipeline-grid {
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }

    .pipeline-step ul,
    .capability-card ul {
        margin: 0;
        padding-left: 1.2rem;
        color: rgba(248, 249, 255, 0.75);
    }

    .pipeline-step header {
        margin-bottom: 1rem;
    }

    .supercompute {
        background: rgba(12, 16, 48, 0.45);
    }

    .supercompute-grid {
        display: grid;
        gap: 2rem;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }

    .supercompute-overview,
    .supercompute-layer,
    .supercompute-status {
        background: var(--card);
        border: 1px solid var(--card-border);
        border-radius: 24px;
        padding: 1.5rem;
        box-shadow: var(--shadow);
    }

    .supercompute-overview ul,
    .supercompute-status ul,
    .supercompute-layer ul {
        margin: 0.5rem 0 0;
        padding-left: 1.25rem;
    }

    .supercompute-layer ul li,
    .supercompute-status ul li {
        margin-bottom: 0.4rem;
    }

    .supercompute-layers {
        display: grid;
        gap: 1.25rem;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }

    .supercompute-status .capability-list {
        list-style: none;
        padding-left: 0;
        margin: 0;
    }

    .supercompute-status .capability-list li {
        margin-bottom: 0.35rem;
    }

    .supercompute-status .capability-list .dim {
        opacity: 0.6;
        font-size: 0.9em;
    }

    .supercompute-status .empty {
        opacity: 0.6;
        font-style: italic;
    }

    .supercompute-status .action-list,
    .supercompute-status .note-list {
        padding-left: 1.25rem;
        margin-top: 0.5rem;
    }

    .capability-grid {
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    }

    .capability-card .category {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        color: rgba(248, 249, 255, 0.65);
    }

    .capability-card section {
        margin-top: 1rem;
    }

    .capability-card h4 {
        margin-bottom: 0.35rem;
        font-size: 0.95rem;
        color: rgba(248, 249, 255, 0.85);
    }

    .offline {
        margin-top: 1.25rem;
        font-size: 0.85rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(248, 249, 255, 0.55);
    }

    .gallery-grid {
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }
    .automation-card pre {
        background: rgba(6, 10, 28, 0.75);
        border-radius: 16px;
        padding: 1rem;
        overflow-x: auto;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .automation-steps {
        margin: 0;
        padding-left: 1.2rem;
        color: rgba(248, 249, 255, 0.75);
    }

    .automation-steps li + li {
        margin-top: 0.35rem;
    }

    .regulation-grid {
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    }

    .regulation-card ul {
        margin: 0;
        padding-left: 1.2rem;
        color: rgba(248, 249, 255, 0.75);
    }

    .regulation-card .jurisdiction,
    .regulation-card .scale {
        font-size: 0.9rem;
        color: rgba(248, 249, 255, 0.7);
    }

    .regulation-card a {
        color: var(--accent-secondary);
    }


    .gallery-card {
        padding: 0;
        overflow: hidden;
    }

    .gallery-card img {
        display: block;
        width: 100%;
        height: auto;
    }

    .gallery-card figcaption {
        padding: 1rem 1.5rem;
        color: rgba(248, 249, 255, 0.75);
    }

    .download {
        text-align: center;
    }

    .download .hint {
        margin-top: 1rem;
        color: rgba(248, 249, 255, 0.65);
    }

    .download code {
        background: rgba(10, 10, 26, 0.75);
        padding: 0.35rem 0.65rem;
        border-radius: 8px;
        font-family: 'Fira Code', 'SFMono-Regular', monospace;
    }

    .footer {
        padding: 2.5rem clamp(1.5rem, 6vw, 6rem) 3rem;
        text-align: center;
        font-size: 0.9rem;
        color: rgba(248, 249, 255, 0.6);
        border-top: 1px solid rgba(248, 249, 255, 0.08);
        background: rgba(6, 6, 16, 0.75);
        backdrop-filter: blur(16px);
    }

    @media (max-width: 640px) {
        .hero {
            padding-top: 4.5rem;
        }

        .hero-actions {
            flex-direction: column;
            align-items: stretch;
        }
    }
    """
)


JS_LOGIC = textwrap.dedent(
    """
    const links = document.querySelectorAll('a[href^="/"]');
    links.forEach((link) => {
        link.addEventListener('click', (event) => {
            const target = link.getAttribute('href');
            if (target.startsWith('/')) {
                event.preventDefault();
                const element = document.getElementById(target.substring(1));
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });
    """
)


BUNDLE_TARGETS: tuple[Path, ...] = (
    Path("README.md"),
    Path("LICENSE"),
    Path("docs/auto3d-pipeline.md"),
    Path("auto3d"),
    Path("scripts/auto3d_cli.py"),
    Path("scripts/auto3d_setup.py"),
    Path("scripts/auto3d_run.py"),
    Path("scripts/auto3d_do_it_for_me.py"),
    Path("scripts/auto3d_prompt_to_stl.py"),
    Path("scripts/auto3d_test.py"),
)


def build_application_bundle(destination: Path) -> Path:
    """Create a downloadable archive of the Auto3D application helpers."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    bundle_path = destination if destination.suffix == ".zip" else destination.with_suffix(".zip")

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for target in BUNDLE_TARGETS:
            full_path = REPO_ROOT / target
            if not full_path.exists():
                continue
            if full_path.is_dir():
                for file_path in full_path.rglob("*"):
                    if file_path.is_dir() or "__pycache__" in file_path.parts:
                        continue
                    archive.write(file_path, file_path.relative_to(REPO_ROOT))
            else:
                archive.write(full_path, target)
    return bundle_path


def render_site(
    output_dir: Path,
    *,
    capabilities: Sequence[AICapability],
    supercompute_readiness: SupercomputeReadiness,
    supercompute_available: Sequence[AICapability],
    supercompute_missing: Sequence[AICapability],
    protocol: str,
    force: bool = False,
    include_bundle: bool = True,
) -> dict[str, Path]:
    """Render the static marketing site into *output_dir*."""

    if output_dir.exists():
        if force:
            shutil.rmtree(output_dir)
        else:
            raise FileExistsError(f"Site directory already exists: {output_dir}")

    output_dir.mkdir(parents=True)

    assets_dir = output_dir / "assets"
    _write_gallery_assets(assets_dir)

    features_html = _render_features_html(TOP_LEVEL_FEATURES)
    pipeline_html = _render_pipeline_html(PIPELINE_STEPS)
    automation_html = _render_automation_html(automation_guidelines())
    regulations_html = _render_regulations_html(building_code_catalog())
    capability_lookup = {cap.key: cap for cap in capabilities}
    capabilities_html = _render_capabilities_html(capabilities)
    supercompute_html = _render_supercompute_html(
        supercompute_readiness,
        supercompute_available,
        supercompute_missing,
        capability_lookup,
    )
    gallery_html = _render_gallery_html(GALLERY_IMAGES)

    download_href = "#"
    download_enabled = False
    downloads_dir = output_dir / "downloads"
    bundle_path: Path | None = None
    if include_bundle:
        downloads_dir.mkdir(exist_ok=True)
        bundle_path = build_application_bundle(downloads_dir / "auto3d-application.zip")
        download_href = str(Path("downloads") / bundle_path.name)
        download_enabled = True

    html = _build_html_document(
        protocol=protocol,
        features_html=features_html,
        pipeline_html=pipeline_html,
        automation_html=automation_html,
        regulations_html=regulations_html,
        capabilities_html=capabilities_html,
        supercompute_html=supercompute_html,
        gallery_html=gallery_html,
        download_href=download_href,
        download_enabled=download_enabled,
    )

    _write_file(output_dir / "index.html", html)
    _write_file(output_dir / "styles.css", CSS_STYLES)
    _write_file(output_dir / "script.js", JS_LOGIC)

    outputs: dict[str, Path] = {
        "index": output_dir / "index.html",
        "styles": output_dir / "styles.css",
        "script": output_dir / "script.js",
    }
    if bundle_path is not None:
        outputs["bundle"] = bundle_path
    return outputs

