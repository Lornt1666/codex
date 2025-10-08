"""Printability heuristics and reporting helpers for generated STL files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


MIN_TRIANGLES_DEFAULT = 12
MIN_THICKNESS_MM_DEFAULT = 0.6
MIN_FOOTPRINT_AREA_MM2_DEFAULT = 25.0


@dataclass(frozen=True)
class STLAnalysis:
    """Summary metrics for a single STL asset."""

    path: Path
    name: str
    triangle_count: int
    vertex_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_y - self.min_y

    @property
    def thickness(self) -> float:
        return self.max_z - self.min_z

    @property
    def footprint_area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.depth)


@dataclass(frozen=True)
class PrintabilityIssue:
    """An actionable finding from the printability gate."""

    level: str  # "error" or "warning"
    message: str


@dataclass(frozen=True)
class PrintabilityResult:
    """Aggregate outcome from the printability heuristics."""

    analyses: tuple[STLAnalysis, ...]
    issues: tuple[PrintabilityIssue, ...]
    recommendations: tuple[str, ...]

    @property
    def success(self) -> bool:
        return all(issue.level != "error" for issue in self.issues)


def _parse_ascii_stl(path: Path) -> STLAnalysis:
    triangle_count = 0
    vertex_count = 0
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("facet normal"):
                triangle_count += 1
                continue
            if not line.startswith("vertex"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                x, y, z = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError:
                continue
            vertex_count += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_z = min(min_z, z)
            max_z = max(max_z, z)

    if vertex_count == 0:
        min_x = max_x = min_y = max_y = min_z = max_z = 0.0

    return STLAnalysis(
        path=path,
        name=path.name,
        triangle_count=triangle_count,
        vertex_count=vertex_count,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_z=min_z,
        max_z=max_z,
    )


def evaluate_printability(
    paths: Sequence[Path],
    *,
    min_triangle_count: int = MIN_TRIANGLES_DEFAULT,
    min_thickness_mm: float = MIN_THICKNESS_MM_DEFAULT,
    min_footprint_mm2: float = MIN_FOOTPRINT_AREA_MM2_DEFAULT,
) -> PrintabilityResult:
    """Evaluate STL files and surface potential print issues."""

    analyses = tuple(_parse_ascii_stl(path) for path in paths)
    issues: list[PrintabilityIssue] = []

    for analysis in analyses:
        if analysis.triangle_count == 0:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=f"{analysis.name}: contains no triangle facets.",
                )
            )
        if analysis.vertex_count % 3 != 0:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=f"{analysis.name}: vertex count is not a multiple of three.",
                )
            )
        if analysis.triangle_count < min_triangle_count:
            issues.append(
                PrintabilityIssue(
                    level="warning",
                    message=(
                        f"{analysis.name}: only {analysis.triangle_count} triangles;"
                        " consider higher tessellation for smoother prints."
                    ),
                )
            )
        if analysis.thickness <= 0.0:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=f"{analysis.name}: zero thickness detected; extrusion failed.",
                )
            )
        elif analysis.thickness < min_thickness_mm:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=(
                        f"{analysis.name}: thickness {analysis.thickness:.2f} mm below"
                        f" minimum {min_thickness_mm:.2f} mm."
                    ),
                )
            )
        if analysis.width <= 0.0 or analysis.depth <= 0.0:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=f"{analysis.name}: footprint collapsed; check polygon winding.",
                )
            )
        elif analysis.footprint_area < min_footprint_mm2:
            issues.append(
                PrintabilityIssue(
                    level="warning",
                    message=(
                        f"{analysis.name}: footprint {analysis.footprint_area:.1f} mm² is"
                        " very small—confirm printer tolerances."
                    ),
                )
            )

    floor_analyses = [analysis for analysis in analyses if "floor" in analysis.name.lower()]
    assembled = next((analysis for analysis in analyses if analysis.name.lower().startswith("assembled")), None)
    if assembled and floor_analyses:
        total_floor_height = sum(analysis.thickness for analysis in floor_analyses)
        if assembled.thickness + 0.1 < total_floor_height:
            issues.append(
                PrintabilityIssue(
                    level="error",
                    message=(
                        "assembled.stl: shorter than combined floor stack; verify"
                        " scaling and roof height settings."
                    ),
                )
            )

    recommendations: list[str] = []
    if any("thickness" in issue.message for issue in issues):
        recommendations.append("Increase scale or adjust floor heights to maintain >0.6 mm shells.")
    if any("triangle" in issue.message for issue in issues):
        recommendations.append("Regenerate STL with higher tessellation or export resolution.")
    if any("footprint" in issue.message for issue in issues):
        recommendations.append("Verify slicer first-layer adhesion settings for very small parts.")
    if not issues:
        recommendations.append("Ready for slicing—run through your printer's preview before fabrication.")

    return PrintabilityResult(
        analyses=analyses,
        issues=tuple(issues),
        recommendations=tuple(dict.fromkeys(recommendations)),
    )


def render_printability_markdown(result: PrintabilityResult, *, include_header: bool = True) -> str:
    """Return a Markdown summary for inclusion in reports."""

    lines: list[str] = []
    if include_header:
        lines.append("## Printability Gate")
        lines.append("")

    status = "PASS" if result.success else "ACTION REQUIRED"
    lines.append(f"- Status: **{status}**")

    if result.issues:
        lines.append("- Findings:")
        for issue in result.issues:
            prefix = "  -" if issue.level == "warning" else "  -"
            label = "warning" if issue.level == "warning" else "error"
            lines.append(f"{prefix} ({label}) {issue.message}")
    else:
        lines.append("- Findings: No blocking issues detected.")

    lines.append("- Metrics:")
    for analysis in result.analyses:
        lines.append(
            "  - "
            f"{analysis.name}: {analysis.triangle_count} tris, "
            f"{analysis.width:.2f}×{analysis.depth:.2f} mm footprint, "
            f"{analysis.thickness:.2f} mm tall"
        )

    if result.recommendations:
        lines.append("- Recommendations:")
        for rec in result.recommendations:
            lines.append(f"  - {rec}")

    lines.append("")
    return "\n".join(lines)


def write_printability_report(
    destination: Path,
    result: PrintabilityResult,
    *,
    name: str = "printability.md",
) -> Path:
    """Write a standalone Markdown report for the printability gate."""

    destination.mkdir(parents=True, exist_ok=True)
    path = destination / name
    path.write_text(render_printability_markdown(result, include_header=True), encoding="utf-8")
    print(f"[printability] Wrote {path}")
    return path


__all__ = [
    "PrintabilityIssue",
    "PrintabilityResult",
    "STLAnalysis",
    "evaluate_printability",
    "render_printability_markdown",
    "write_printability_report",
]
