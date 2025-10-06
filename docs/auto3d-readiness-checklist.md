# Auto3D readiness checklist

Use this checklist when you need to confirm that the Auto3D toolkit covers the end-to-end workflow you described: prompt ingestion, synthetic geometry generation, STL floor slicing, printability verification, automation hooks, and the supercomputing readiness blueprint. Each section links back to the command(s) or modules that already ship in this repository.

## 1. Workspace and assets
- [ ] Bootstrap or refresh a workspace with `python -m auto3d --workspace <path> setup`.
- [ ] Capture your hero render(s) or descriptive prompt.  Use the prompt-to-STL generator (`python -m auto3d … prompt`) when imagery is unavailable.
- [ ] Verify floor bands (`configs/floors.yaml`) or supply them via CLI flags before slicing.

## 2. Geometry generation options
- [ ] Single-image TripoSR run: `python -m auto3d … pipeline --use-triposr`.
- [ ] Catalog-driven prompt variants: `python -m auto3d … prompt --catalog variant-id`.
- [ ] Mission-control static site + bundle for distribution: `python -m auto3d … web --output <dir> --bundle`.

## 3. Mesh cleanup and enhancement
- [ ] Blender macro (`scripts/auto3d_setup.py` drops `auto_cleanup.py`) executed for wall solidification and floor snapping.
- [ ] Optional catalog enrichments (garages, towers, dormers, porches, chimneys) enabled through prompt features in `auto3d.prompt`.
- [ ] Supercomputing readiness blueprint exported via `python -m auto3d … supercompute` if distributed orchestration is required.

## 4. Floor slicing and previews
- [ ] Primary slicer: `python -m auto3d … pipeline --slice` or `python -m auto3d … slice` route in the CLI.
- [ ] Exploded view generator (`auto3d.site` bundle) exported for visual QA.
- [ ] Scaling and reporting handled via prompt runner output (`reports/*.md`) and preview assets in the site bundle.

## 5. Quality gates
- [ ] Run regression guard: `python -m auto3d … test` (wraps `compileall` + targeted `pytest`).
- [ ] Printability heuristics: `python -m auto3d … printability --input outputs/*.stl --report reports/printability.md`.
- [ ] Automation harness: generate Playwright upload scripts with `python -m auto3d … automation --platform <name>`.

## 6. Documentation and distribution
- [ ] Marketing / mission-control site regenerated (`python -m auto3d … web --serve` for previews).
- [ ] README navigation points to this checklist and the pipeline guide for onboarding.
- [ ] Building-code catalog exported for the relevant provinces/states via `python -m auto3d … regulations --region <code>`.

## 7. Final go / no-go questions
- [ ] Do generated STL stacks pass the printability report with no blockers?
- [ ] Are automation scripts updated with current upload targets and credentials?
- [ ] Have the supercomputing blueprint and AI capability catalog been reviewed with stakeholders who need sign-off?
- [ ] Is the latest bundle mirrored to your preferred hosting/distribution channel?

If every box is ticked, the Auto3D toolchain contains all the pieces requested so far.  Use this checklist as a recurring QA gate whenever you extend the pipeline with new variants, automation targets, or compliance regions.
