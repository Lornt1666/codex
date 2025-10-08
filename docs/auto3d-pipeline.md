# Auto-generate the Auto3D Render-to-STL workspace

The `auto3d_setup.py` helper script creates the same folder structure and scripts that were shared in the Auto3D walkthrough. It
lets you bootstrap a fresh workspace on any machine with a single command, instead of manually recreating each file.

## Prerequisites

- Python 3.10 or newer.
- (Optional) [Codex CLI](../README.md) if you want Codex to run the script for you.

## 0. Unified CLI wrapper (`python -m auto3d`)

If you would rather treat everything as an “application” instead of juggling multiple scripts, run the new package entrypoint:

```bash
python -m auto3d --workspace Auto3D-Render-to-STL setup
```

This single interface exposes all of the helper flows:

| Subcommand | What it does |
| --- | --- |
| `setup` | Creates the scaffolded workspace (same as `auto3d_setup.py`). |
| `pipeline` | Runs the TripoSR → slicer orchestration (same as `auto3d_run.py`). |
| `prompt` | Generates watertight STL shells straight from a descriptive prompt (same as `auto3d_prompt_to_stl.py`). |
| `wizard` | Launches the interactive “do it for me” flow, or replays saved defaults (`auto3d_do_it_for_me.py`). |
| `printability` | Checks a stack of STL files against the printability gate and emits a Markdown report. |
| `test` | Compiles the Auto3D modules and executes the targeted regression tests. |

Each command accepts the same flags as the standalone scripts. For example, to go from the descriptive prompt you shared straight
to floor STLs and a millimetre-by-millimetre report:

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  prompt \
  --prompt "Coordinate a feature of rendering a house design … 4 bedroom 2 bath unfinished basement" \
  --protocol "1JGM∞.BE"
```

Prefer sticking with the scripts folder? `python scripts/auto3d_cli.py …` is a thin wrapper around the same interface.

You can still use the individual scripts below if you prefer to call them directly. The underlying functionality is identical –
the CLI wrapper simply wires them together so the toolkit behaves like a cohesive application.

## 0. Beginner-friendly wizard

Run the interactive helper if you want the script to guide you step by step and remember your answers for next time:

```bash
python scripts/auto3d_do_it_for_me.py
```

The wizard will ask where to create the workspace, which render to use, and whether to run TripoSR or the slicer immediately. At the end you can choose to save the answers to `~/.auto3d_do_it_for_me.json`. Future runs can reuse that file automatically:

```bash
python scripts/auto3d_do_it_for_me.py --auto
```

Use `--reset` if you want to ignore the saved defaults for a single run.

## 0.5 Prompt-to-STL fallback (no external 3D tools required)

Need something printable right away without installing TripoSR or photogrammetry? The prompt-driven generator synthesises a
three-part stack (basement, main, upper floors, plus an optional roof) with watertight STL shells using only standard Python.
It interprets bedroom/bath counts, basement hints, and style cues from your prompt and estimates sensible square-footage ratios
down to centimetres and millimetres.

```bash
python scripts/auto3d_prompt_to_stl.py \
  --prompt "4 bedroom 2 bath unfinished basement with light brown timber trim and charcoal stone base" \
  --hero renders/front_view.png
```

Key behaviour:

- Creates or refreshes the Auto3D workspace (same as `auto3d_setup.py`).
- Copies the optional hero render into `input_images/` for context.
- Emits `outputs/floor_00_basement.stl`, `outputs/floor_01_main.stl`, `outputs/floor_02_upper1.stl`, `outputs/roof.stl`, and
  `outputs/assembled.stl`.
- Writes `outputs/auto3d_prompt_report.md` summarising the parsed programme, real-world dimensions, and the model-scale
  conversions down to centimetres and millimetres (default 1:100; override with `--model-scale`).
- Synthesises a full massing pass – garage wing, stepped upper floor, covered porch, dormer, chimney, and optional wings or
  spires – so that unseen facades are still represented when you only have a single hero view.
- Runs the printability gate on every STL (min thickness, footprint sanity, stack height check) and writes
  `outputs/printability.md`. Any error-level findings abort the command so you never queue an unprintable file.

The geometry is intentionally simplified—rectilinear shells sized for hand-held prints—so you can iterate immediately while
you work on higher-fidelity meshes, but the prompt cues now feed into a richer layout so the STL stack looks deliberate even when
you never modelled the back or sides by hand.

## 0.75 Prompt catalog (auto variation library)

Need a gallery of plausible options for review? The catalog command generates a set of STL stacks and
reports by applying curated massing variants (manor wing, courtyard terrace, compact infill, gothic
spire, skyline atrium, etc.) to the same descriptive prompt. New style-aware variants trigger
automatically — Scottish or Irish prompts add highland keeps, Nordic briefs get pavilion wings,
Dutch cues unlock stepped gables, Canadian/American notes expand porches and garages, poetic
prompts pick up storybook turrets, and legendary engineering language now raises a flying buttress
array around the primary halls.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  catalog \
  --prompt "4 bedroom 2 bath unfinished basement with Scandinavian timber and charcoal stone" \
  --protocol "1JGM∞.BE"
```

Key behaviour:

- Writes each variant to `outputs/catalog/<variant>/` with floor STLs, an optional roof, an assembled
  stack, and a `report.md` detailing the changes.
- Adds a per-variant `printability.md` so every catalog entry passes the same thickness/footprint checks as the base generator.
- Produces `outputs/catalog/_index.md` summarising every variant with links back to the assets.
- Accepts `--limit` if you only want the first _n_ variants, plus `--no-roof` if you only care about
  the floor plates.
- Shares the same prompt parser and dimension heuristics as the base generator, so centimetre and
  millimetre breakdowns stay in sync across the catalog.

```bash
# Generate a compact-only catalog without roofs
python -m auto3d --workspace Auto3D-Render-to-STL \
  catalog \
  --prompt-file prompts/my_house.txt \
  --limit 1 \
  --no-roof
```

Prefer the script wrapper?

```bash
python scripts/auto3d_cli.py --workspace Auto3D-Render-to-STL catalog --prompt "..."
```

## 0.78 Standalone printability gate (reuse on any STL stack)

Need to re-check a mesh after manual edits or run the quality gate on a catalog variant before you share it? The `printability`
subcommand uses the exact same heuristics that guard the prompt, catalog, and pipeline flows—triangle counts, wall thickness,
footprint sanity, and assembled stack height—but you can point it at any STL files you want.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  printability \
  --stl outputs/floor_01_main.stl \
  --stl outputs/floor_02_upper.stl \
  --stl outputs/assembled.stl
```

Key behaviour:

- Defaults to `workspace/outputs/*.stl` when you omit `--stl`, so you can simply run `python -m auto3d printability` after
  tweaking floor heights or re-exporting meshes.
- Writes `outputs/printability.md` (or a custom location via `--report-dir` / `--report-name`) and surfaces a condensed console
  summary using the same Markdown renderer embedded in the prompt reports.
- Exits with status code `1` whenever an error-level issue is detected, making it perfect for CI or pre-upload gates alongside
  the Playwright automation flows.

## 0.79 Regression tests (module-level confidence)

The `/test` command and the accompanying `pytest` suite exist to prove the
Python toolkit works as a self-contained module. They compile the Auto3D
package, exercise the prompt-to-STL flow, and validate auxiliary helpers such as
catalog generation, automation scripts, the marketing site builder, and the
printability gate. None of these tests invoke TripoSR, Blender, Meshroom, or any
other external renderer—they only confirm that the code paths inside this repo
produce deterministic, printable assets from the descriptive briefs you
provide.

Because the tests never leave the Python boundary, you can run them in any
environment (CI, Codex, or a local workstation) without configuring GPUs or
photogrammetry stacks. Use them as a health check before sharing a workspace or
publishing a new bundle; rely on your preferred 3D workflow when you are ready
to replace the synthetic shells with artist-authored meshes.

## 0.8 AI capability catalog (research & orchestration helper)

The new `capabilities` command keeps a curated list of AI workflows (TripoSR single-image
reconstruction, ControlNet view synthesis, Meshroom/COLMAP photogrammetry, Nerfstudio gaussian
splatting, Blender Geometry Nodes massing, FreeCAD mesh-to-BREP conversion, MeshFix/Blender repair,
material diffusion texture baking, etc.) and tailors recommendations to the style tags parsed from
your descriptive prompt.

```bash
# Show tailored suggestions for a Scottish / Canadian brief
python -m auto3d --workspace Auto3D-Render-to-STL \
  capabilities \
  --style scottish --style canadian --style picaresque \
  --floors 3 \
  --basement

# Dump the full catalog to JSON for further tooling
python -m auto3d --workspace Auto3D-Render-to-STL capabilities --catalog --format json
```

Every prompt-driven report now embeds a "Recommended AI Capability Stack" section summarising the
best-fit tools (including availability notes and provider references) alongside the centimetre and
millimetre dimension breakdowns. Use it as a launchpad when you’re ready to swap the heuristic STL
fallback for higher fidelity AI workflows.

## 0.85 Supercomputing blueprint readiness

Need to prove this pipeline aligns with the "artificial super computing intelligence" vision? The
`supercompute` command evaluates the canonical 1JGM∞.BE blueprint, lists every layer (ingestion,
reconstruction, conversion, orchestration), and tells you which AI capabilities you already have in
place versus the ones you still need to integrate.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  supercompute \
  --capability tripo_sr_single_image \
  --capability meshroom_photogrammetry \
  --capability distributed_hpc_orchestration
```

Use `--format json` when you want to feed the readiness report back into Codex or other automation
scripts, or point it at a different protocol tag with `--protocol`. Pair it with the AI capability
catalog and regulation atlas to show that every requirement Justice Gray Maciocha (aka Satoshi
_amamoto / Lornt) listed is covered—from GPU ingestion rigs through HPC schedulers and energy
telemetry.

## 0.9 Static mission-control website + download bundle

Need a shareable, always-on overview that sells the workflow and hands collaborators a ready-made
toolkit? The new `web` command builds a full marketing site—complete with protocol 1JGM∞.BE
branding, supercomputing-flavoured imagery, navigation across every route you listed, and a
download button that packages the Auto3D scripts, docs, and CLI entrypoint.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  web \
  --output Auto3D-Render-to-STL/site \
  --serve --open-browser
```

Pass `--no-bundle` when you only want the static site, or `--serve`/`--open-browser` to spin up a
local preview server that automatically opens in your browser. Use `Ctrl+C` to stop the preview.

## 1.0 Playwright automation (upload flows, marketplace staging)

When you are ready to push the generated STLs into storefronts (Shopify, Amazon Seller Central,
etc.), the `automation` command produces a tailored [Playwright](https://playwright.dev) script that
opens the target page, steps through your selectors, uploads an STL, and waits for completion.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  automation \
  --url "https://seller.example.com/upload" \
  --upload-path Auto3D-Render-to-STL/outputs/assembled.stl \
  --start "button#start" \
  --upload-selector "input[type=file]" \
  --submit "button[data-action=save]" \
  --note "Login beforehand or reuse Playwright auth storage" \
  --note "Staging only: confirm price + SKU before headless runs"
```

Key points:

- Defaults to `outputs/assembled.stl`; override the path if you want to upload a specific floor.
- Repeat `--start` and `--click` for extra buttons the script should trigger before/after the
  upload.
- Use `--headless` once selectors are stable; otherwise watch the browser (`headless` off) so you
  can visually confirm each step.
- The generated script lands in `workspace/automation/auto3d_playwright_upload.py` (override with
  `--output`).
- Each run prints best-practice tips (install Playwright, keep selectors stable, store secrets
  safely, run dry-run tests) so your automation remains reliable.

Want to orchestrate it from the scripts folder instead of the package?

```bash
python scripts/auto3d_cli.py --workspace Auto3D-Render-to-STL automation --url ...
```

## 1.1 Regional building-code references (Alberta → national → continental)

The new `regulations` command curates key building-code and permit references so your STL reports
can cite the right jurisdictional context—crucial when selling models to developers, schools, or
engineering teams that need to align with Alberta standards.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  regulations \
  --region alberta \
  --scale residential \
  --keyword energy
```

Default output is a human-readable list; add `--format json` to feed the catalog into other tools or
`--limit` to grab just a couple of entries. All references note how they map onto toy-scale prints,
full residential submissions, and broader North American energy requirements so you can tailor your
reports to any audience.

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  web \
  --output Auto3D-Render-to-STL/site \
  --protocol "1JGM∞.BE" \
  --serve \
  --open-browser
```

Key behaviour:

- Wipes the output directory first when you pass `--force`, then writes `index.html`, `styles.css`,
  and `script.js` plus branded SVG artwork and a `/downloads/auto3d-application.zip` bundle.
- Mirrors the navigation routes you requested (`/home`, `/projects`, `/upload`, `/convert`,
  `/cleanup`, `/slice`, `/preview`, `/download`, `/settings`, `/help`) so designers and devs can map
  their components directly.
- Pulls the latest AI capability catalog into the page so prospects see every recommended workflow
  (TripoSR, ControlNet, Meshroom, Nerfstudio, Geometry Nodes, FreeCAD, MeshFix, texture diffusion,
  etc.) without opening a terminal.
- Includes gradient-backed “supercomputer” imagery referencing Justice Gray Maciocha,
  Satoshi _amamoto, and Lornt for continuity with your aliases.
- Pass `--serve` to spawn a local preview server (default `http://127.0.0.1:8000/`) and optionally
  `--open-browser` to launch your default browser automatically. Hit `Ctrl+C` to stop the preview
  and re-run the command whenever the scripts update—the download bundle is regenerated each time.
- Deploy by copying the generated folder to any static host (GitHub Pages, Netlify Drop, S3, etc.).

## 0.95 Quality gate (`/test` between runs)

Want a quick sanity check after every script tweak? The CLI now exposes a `test` command that mirrors the
manual compile-and-unittest sequence we have been running in this walkthrough. Use it whenever you finish a
"coordination of individualized codetures" so you always end with a clean green suite:

```bash
python -m auto3d --workspace Auto3D-Render-to-STL \
  test \
  --module tests.test_auto3d_prompt_to_stl \
  --module tests.test_auto3d_capabilities \
  --module tests.test_auto3d_site \
  --module tests.test_auto3d_cli
```

By default the command runs the bundled compileall check and the curated regression modules (prompt-to-STL,
catalog, site builder, and CLI quality gates). Skip the compile step with `--skip-compile` or narrow the
tests to a specific module with repeated `--module` flags.

Prefer staying inside the scripts folder? The new `scripts/auto3d_test.py` wrapper forwards the same
options:

```bash
python scripts/auto3d_test.py --skip-compile --module tests.test_auto3d_cli
```

Both entrypoints call the new `Auto3DApplication.run_tests` helper, so Codex CLI or any automation script
can trigger the exact same quality gate after each action.

## 1. "Do it for me" helper

If you want a single command that scaffolds the workspace, copies your hero image, runs TripoSR, and slices floors, use the turnkey runner:

```bash
python scripts/auto3d_run.py \
  --hero "D:/Renders/house.png" \
  --triposr-command "python D:/Tools/TripoSR/demo.py --input {input} --output {output}"
```

Key flags:

- `--workspace` – where to create or reuse the Auto3D folder.
- `--hero` – image to copy into `input_images/` (optional).
- `--triposr-command` – command template that generates the mesh. Use `{input}` and `{output}` placeholders.
- `--skip-triposr` / `--skip-slicer` – run only part of the pipeline.
- `--python` – choose a specific interpreter for running the slicer script.

The runner calls into the same scaffolding logic as the setup script, so you can rerun it safely; add `--force` if you want to overwrite template files.

## 2. Generate the workspace

From the root of this repository run:

```bash
python scripts/auto3d_setup.py
```

This creates an `Auto3D-Render-to-STL` directory alongside your current working directory. Pass a custom destination if you want
a different path:

```bash
python scripts/auto3d_setup.py "D:/Projects/MyHousePrinter"
```

Use `--force` to overwrite existing files.

## 3. What the script installs

`auto3d_setup.py` creates:

- `README.md` – quick-start instructions.
- `configs/floors.yaml` – default floor slicing configuration.
- `scripts/2_slice_mesh_to_floors.py` – floor slicer.
- `scripts/3_blender_floor_exploder.py` – optional Blender exploded-view exporter.
- `scripts/auto_cleanup.py` – Blender macro for mesh cleanup.
- `scripts/run_pipeline.bat` – Windows batch file orchestrating the workflow.
- `scripts/1_notes_triposr.md` – reminder on producing meshes with TripoSR.
- Supporting folders: `input_images/`, `working/`, `outputs/`.

Everything is MIT-licensed so you can remix it for your own projects.

## 4. Run the pipeline

1. Drop your hero render into `input_images/hero.png`.
2. Produce `working/house_mesh.obj` using [TripoSR](https://github.com/VAST-AI-Research/TripoSR) or a multi-view photogrammetry
   tool.
3. Edit `configs/floors.yaml` to match your floor heights.
4. Slice the mesh:

   ```powershell
   python scripts\2_slice_mesh_to_floors.py --mesh "working\house_mesh.obj" --config "configs\floors.yaml" --outdir "outputs"
   ```

5. (Optional) In Blender run `scripts/auto_cleanup.py` followed by `scripts/3_blender_floor_exploder.py` for inspection exports.

## 5. Automating with Codex CLI (optional)

You can let Codex run everything non-interactively by combining the script with `codex exec`:

```bash
codex exec --full-auto -- "Create the Auto3D-Render-to-STL workspace by running python scripts/auto3d_setup.py"
```

Codex will execute the command, stream progress, and leave the generated files on disk. Add extra instructions in the quoted
prompt if you want Codex to immediately run TripoSR or the slicer afterwards.

## 6. Next steps

- Print a low-resolution draft to verify the floor splits.
- Swap in multi-view photogrammetry meshes when you need higher fidelity.
- Extend `auto3d_setup.py` with your own templates (custom README, slicer defaults, etc.).

Enjoy the one-command setup!
