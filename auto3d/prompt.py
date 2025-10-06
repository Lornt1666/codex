"""Generate massed STL outputs directly from a descriptive prompt."""
from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from auto3d.capabilities import recommended_capabilities
from auto3d.printability import (
    PrintabilityResult,
    evaluate_printability,
    render_printability_markdown,
    write_printability_report,
)
from auto3d.setup import create_project

FEET_TO_METERS = 0.3048
DEFAULT_MODEL_SCALE = 100.0  # 1:100 ratio (real meters / model meters)
DEFAULT_WORKSPACE = Path("Auto3D-Render-to-STL")
DEFAULT_PROTOCOL = "1JGM∞.BE"


@dataclass
class PromptConfig:
    bedrooms: int
    bathrooms: float
    floors_above: int
    has_basement: bool
    declared_square_feet: float | None
    style_tags: list[str]


@dataclass
class FloorSpec:
    key: str
    label: str
    height_m: float
    area_sqft: float
    level: int


@dataclass
class GarageSpec:
    width_ft: float
    depth_ft: float
    offset_ft: float


@dataclass
class PorchSpec:
    width_ft: float
    depth_ft: float
    offset_ft: float


@dataclass
class ChimneySpec:
    width_ft: float
    depth_ft: float
    offset_ft: float
    depth_offset_ft: float


@dataclass
class WingSpec:
    key: str
    label: str
    x_ft: float
    y_ft: float
    width_ft: float
    depth_ft: float
    min_level: int
    max_level: int


@dataclass
class TowerSpec:
    key: str
    label: str
    center_x_ft: float
    center_y_ft: float
    radius_ft: float
    base_level: int
    top_level: int
    height_scale: float = 1.0
    segments: int = 12
    roof_height_ft: float | None = None


@dataclass
class ButtressSpec:
    key: str
    label: str
    base_x_ft: float
    base_y_ft: float
    width_ft: float
    depth_ft: float
    base_level: int
    top_level: int
    direction: str = "x+"
    flying: bool = False
    bridge_length_ft: float = 0.0
    bridge_height_ft: float = 1.0


@dataclass
class Geometry:
    main_width_ft: float
    main_depth_ft: float
    floors: list[FloorSpec]
    roof_height_ft: float
    garage: GarageSpec | None
    porch: PorchSpec | None
    chimney: ChimneySpec | None
    wings: list[WingSpec]
    towers: list[TowerSpec]
    buttresses: list[ButtressSpec]
    notes: list[str]

    @property
    def width_ft(self) -> float:
        min_x = 0.0
        max_x = self.main_width_ft
        for tower in self.towers:
            min_x = min(min_x, tower.center_x_ft - tower.radius_ft)
            max_x = max(max_x, tower.center_x_ft + tower.radius_ft)
        for buttress in self.buttresses:
            min_x = min(min_x, buttress.base_x_ft)
            max_x = max(max_x, buttress.base_x_ft + buttress.width_ft)
            if buttress.flying:
                if buttress.direction == "x-":
                    min_x = min(min_x, buttress.base_x_ft - buttress.bridge_length_ft)
                if buttress.direction == "x+":
                    max_x = max(max_x, buttress.base_x_ft + buttress.width_ft + buttress.bridge_length_ft)
        return max_x - min_x

    @property
    def total_depth_ft(self) -> float:
        min_y = 0.0
        max_y = (self.garage.depth_ft if self.garage else 0.0) + self.main_depth_ft
        for wing in self.wings:
            max_y = max(max_y, wing.y_ft + wing.depth_ft)
        for tower in self.towers:
            min_y = min(min_y, tower.center_y_ft - tower.radius_ft)
            max_y = max(max_y, tower.center_y_ft + tower.radius_ft)
        for buttress in self.buttresses:
            min_y = min(min_y, buttress.base_y_ft)
            max_y = max(max_y, buttress.base_y_ft + buttress.depth_ft)
            if buttress.flying:
                if buttress.direction == "y-":
                    min_y = min(min_y, buttress.base_y_ft - buttress.bridge_length_ft)
                if buttress.direction == "y+":
                    max_y = max(
                        max_y,
                        buttress.base_y_ft + buttress.depth_ft + buttress.bridge_length_ft,
                    )
        return max_y - min_y


@dataclass
class ModelDimensions:
    width_mm: float
    depth_mm: float
    floor_heights_mm: list[float]
    roof_height_mm: float
    scale: float


def clone_floor(spec: FloorSpec) -> FloorSpec:
    return FloorSpec(
        key=spec.key,
        label=spec.label,
        height_m=spec.height_m,
        area_sqft=spec.area_sqft,
        level=spec.level,
    )


def clone_geometry(geometry: Geometry) -> Geometry:
    return Geometry(
        main_width_ft=geometry.main_width_ft,
        main_depth_ft=geometry.main_depth_ft,
        floors=[clone_floor(spec) for spec in geometry.floors],
        roof_height_ft=geometry.roof_height_ft,
        garage=GarageSpec(
            width_ft=geometry.garage.width_ft,
            depth_ft=geometry.garage.depth_ft,
            offset_ft=geometry.garage.offset_ft,
        )
        if geometry.garage
        else None,
        porch=PorchSpec(
            width_ft=geometry.porch.width_ft,
            depth_ft=geometry.porch.depth_ft,
            offset_ft=geometry.porch.offset_ft,
        )
        if geometry.porch
        else None,
        chimney=ChimneySpec(
            width_ft=geometry.chimney.width_ft,
            depth_ft=geometry.chimney.depth_ft,
            offset_ft=geometry.chimney.offset_ft,
            depth_offset_ft=geometry.chimney.depth_offset_ft,
        )
        if geometry.chimney
        else None,
        wings=[
            WingSpec(
                key=wing.key,
                label=wing.label,
                x_ft=wing.x_ft,
                y_ft=wing.y_ft,
                width_ft=wing.width_ft,
                depth_ft=wing.depth_ft,
                min_level=wing.min_level,
                max_level=wing.max_level,
            )
            for wing in geometry.wings
        ],
        towers=[
            TowerSpec(
                key=tower.key,
                label=tower.label,
                center_x_ft=tower.center_x_ft,
                center_y_ft=tower.center_y_ft,
                radius_ft=tower.radius_ft,
                base_level=tower.base_level,
                top_level=tower.top_level,
                height_scale=tower.height_scale,
                segments=tower.segments,
                roof_height_ft=tower.roof_height_ft,
            )
            for tower in geometry.towers
        ],
        buttresses=[
            ButtressSpec(
                key=buttress.key,
                label=buttress.label,
                base_x_ft=buttress.base_x_ft,
                base_y_ft=buttress.base_y_ft,
                width_ft=buttress.width_ft,
                depth_ft=buttress.depth_ft,
                base_level=buttress.base_level,
                top_level=buttress.top_level,
                direction=buttress.direction,
                flying=buttress.flying,
                bridge_length_ft=buttress.bridge_length_ft,
                bridge_height_ft=buttress.bridge_height_ft,
            )
            for buttress in geometry.buttresses
        ],
        notes=list(geometry.notes),
    )


@dataclass
class CatalogVariant:
    key: str
    label: str
    description: str
    adjust: Callable[[PromptConfig, Geometry], Geometry]


def _baseline_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    geom.notes.append("Catalog baseline variant mirrors the prompt-driven massing heuristics.")
    return geom


def _manor_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    front_offset = geom.garage.depth_ft if geom.garage else 0.0
    wing_width = min(max(geom.main_width_ft * 0.45, 18.0), geom.main_width_ft - 3.0)
    wing_depth = geom.main_depth_ft * 0.6
    wing_x = max(1.5, geom.main_width_ft - wing_width - 1.8)
    wing_y = front_offset + geom.main_depth_ft * 0.38
    min_level = 1 if config.has_basement else 0
    max_level = geom.floors[-1].level
    geom.wings.append(
        WingSpec(
            key="manor_rear_wing",
            label="Rear entertaining wing",
            x_ft=wing_x,
            y_ft=wing_y,
            width_ft=wing_width,
            depth_ft=wing_depth,
            min_level=min_level,
            max_level=max_level,
        )
    )
    if geom.porch:
        geom.porch.width_ft = min(geom.main_width_ft * 0.92, geom.porch.width_ft * 1.25)
        geom.porch.offset_ft = max((geom.main_width_ft - geom.porch.width_ft) / 2.0, 0.4)
        geom.porch.depth_ft = max(geom.porch.depth_ft, 8.0)
    else:
        porch_width = geom.main_width_ft * 0.88
        geom.porch = PorchSpec(
            width_ft=porch_width,
            depth_ft=min(9.0, geom.main_depth_ft * 0.4),
            offset_ft=(geom.main_width_ft - porch_width) / 2.0,
        )
    geom.notes.append("Extended entertaining wing and wraparound porch for manor-scale presence.")
    return geom


def _courtyard_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    front_offset = geom.garage.depth_ft if geom.garage else 0.0
    min_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level

    left_width = min(max(geom.main_width_ft * 0.34, 14.0), geom.main_width_ft / 2.2)
    left_depth = geom.main_depth_ft * 0.55
    right_width = min(max(geom.main_width_ft * 0.3, 12.0), geom.main_width_ft / 2.4)
    right_depth = geom.main_depth_ft * 0.48

    geom.wings.extend(
        [
            WingSpec(
                key="courtyard_left",
                label="Garden studio wing",
                x_ft=1.4,
                y_ft=front_offset + geom.main_depth_ft * 0.58,
                width_ft=left_width,
                depth_ft=left_depth,
                min_level=min_level,
                max_level=max(min_level, top_level - 1),
            ),
            WingSpec(
                key="courtyard_right",
                label="Garage loft wing",
                x_ft=max(1.2, geom.main_width_ft - right_width - 1.2),
                y_ft=front_offset + geom.main_depth_ft * 0.18,
                width_ft=right_width,
                depth_ft=right_depth,
                min_level=min_level,
                max_level=top_level,
            ),
        ]
    )
    geom.notes.append("Twin courtyard wings frame a sheltered rear terrace and service yard.")
    return geom


def _gothic_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    base_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level
    tower_radius = max(3.2, geom.main_width_ft * 0.14)
    tower_center_x = geom.main_width_ft * 0.28
    tower_center_y = (geom.garage.depth_ft if geom.garage else 0.0) + geom.main_depth_ft * 0.2
    geom.towers.append(
        TowerSpec(
            key="gothic_front_spire",
            label="Front Gothic spire",
            center_x_ft=tower_center_x,
            center_y_ft=tower_center_y,
            radius_ft=tower_radius,
            base_level=base_level,
            top_level=top_level,
            height_scale=1.2,
            segments=16,
            roof_height_ft=base.roof_height_ft * 1.45,
        )
    )
    geom.roof_height_ft *= 1.18
    geom.notes.append("Gothic-inspired spire and steepened ridge emphasise vertical drama.")
    return geom


def _compact_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    width_scale = 0.9
    depth_scale = 0.88
    geom.main_width_ft *= width_scale
    geom.main_depth_ft *= depth_scale
    for spec in geom.floors:
        spec.area_sqft *= width_scale * depth_scale
    if geom.garage:
        geom.garage.width_ft = max(geom.garage.width_ft * width_scale, 11.0)
        geom.garage.depth_ft *= depth_scale
        max_offset = max(geom.main_width_ft - geom.garage.width_ft - 1.4, 1.2)
        geom.garage.offset_ft = min(max(geom.garage.offset_ft * width_scale, 1.2), max_offset)
    if geom.porch:
        geom.porch.width_ft *= width_scale
        geom.porch.offset_ft = max((geom.main_width_ft - geom.porch.width_ft) / 2.0, 0.5)
        geom.porch.depth_ft = min(geom.porch.depth_ft, 6.5)
    geom.notes.append("Compact infill plan tightens the footprint for urban lots.")
    return geom


def _spire_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    base_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level
    center_x = geom.main_width_ft * 0.5
    center_y = (geom.garage.depth_ft if geom.garage else 0.0) + geom.main_depth_ft * 0.52
    geom.towers.append(
        TowerSpec(
            key="atrium_spire",
            label="Central atrium spire",
            center_x_ft=center_x,
            center_y_ft=center_y,
            radius_ft=max(2.6, geom.main_width_ft * 0.1),
            base_level=base_level,
            top_level=top_level,
            height_scale=1.35,
            segments=14,
            roof_height_ft=base.roof_height_ft * 1.8,
        )
    )
    geom.notes.append("Central atrium spire crowns the stack for skyline-ready silhouettes.")
    return geom


def _highland_keep_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    base_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level
    radius = max(geom.main_width_ft * 0.14, 3.2)
    center_x = max(radius + 1.2, geom.main_width_ft * 0.22)
    center_y = (geom.garage.depth_ft if geom.garage else 0.0) + geom.main_depth_ft * 0.25
    geom.towers.append(
        TowerSpec(
            key="highland_keep",
            label="Stone keep tower",
            center_x_ft=center_x,
            center_y_ft=center_y,
            radius_ft=radius,
            base_level=base_level,
            top_level=top_level,
            height_scale=1.2,
            segments=12,
            roof_height_ft=base.roof_height_ft * 1.3,
        )
    )
    if geom.chimney:
        geom.chimney.width_ft = max(geom.chimney.width_ft, 3.0)
        geom.chimney.depth_ft = max(geom.chimney.depth_ft, 2.6)
    else:
        geom.chimney = ChimneySpec(
            width_ft=3.0,
            depth_ft=2.8,
            offset_ft=max(geom.main_width_ft * 0.18, 2.2),
            depth_offset_ft=max(geom.main_depth_ft * 0.32, 3.0),
        )
    geom.notes.append("Highland keep tower and oversized chimney reinforce stone-forward massing cues.")
    return geom


def _fjordlight_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    front_offset = geom.garage.depth_ft if geom.garage else 0.0
    min_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level

    pavilion_width = min(max(geom.main_width_ft * 0.42, 16.0), geom.main_width_ft - 4.0)
    pavilion_depth = geom.main_depth_ft * 0.38
    geom.wings.append(
        WingSpec(
            key="fjordlight_pavilion",
            label="Glazed pavilion wing",
            x_ft=(geom.main_width_ft - pavilion_width) / 2.0,
            y_ft=front_offset + geom.main_depth_ft * 0.58,
            width_ft=pavilion_width,
            depth_ft=pavilion_depth,
            min_level=min_level,
            max_level=top_level,
        )
    )
    if geom.porch:
        geom.porch.width_ft = min(geom.main_width_ft * 0.96, geom.porch.width_ft * 1.2)
        geom.porch.depth_ft = min(max(geom.porch.depth_ft, 6.0), 7.5)
        geom.porch.offset_ft = max((geom.main_width_ft - geom.porch.width_ft) / 2.0, 0.4)
    else:
        porch_width = geom.main_width_ft * 0.9
        geom.porch = PorchSpec(
            width_ft=porch_width,
            depth_ft=6.5,
            offset_ft=(geom.main_width_ft - porch_width) / 2.0,
        )
    geom.roof_height_ft = base.roof_height_ft * 1.15
    geom.notes.append("Glazed pavilion wing and taller ridge celebrate Nordic light.")
    return geom


def _canal_step_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    front_offset = geom.garage.depth_ft if geom.garage else 0.0
    min_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level

    gable_width = min(max(geom.main_width_ft * 0.28, 12.0), geom.main_width_ft / 2.1)
    centers = [geom.main_width_ft * 0.28, geom.main_width_ft * 0.72]
    for index, center in enumerate(centers):
        geom.towers.append(
            TowerSpec(
                key=f"canal_step_{index}",
                label="Stepped gable cap",
                center_x_ft=center,
                center_y_ft=front_offset + 0.5,
                radius_ft=gable_width / 2.6,
                base_level=min_level,
                top_level=top_level,
                height_scale=1.05 + index * 0.08,
                segments=10,
                roof_height_ft=base.roof_height_ft * (1.15 + 0.08 * index),
            )
        )
    geom.notes.append("Twin stepped gables echo canal-house silhouettes for Dutch cues.")
    return geom


def _northwoods_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    if geom.garage:
        geom.garage.width_ft = max(geom.garage.width_ft * 1.2, 20.0)
        geom.garage.depth_ft = max(geom.garage.depth_ft, 22.0)
        geom.garage.offset_ft = max(1.0, geom.garage.offset_ft * 0.8)
    else:
        geom.garage = GarageSpec(width_ft=22.0, depth_ft=22.0, offset_ft=1.5)
    if geom.porch:
        geom.porch.depth_ft = max(geom.porch.depth_ft, 9.0)
    else:
        porch_width = geom.main_width_ft * 0.8
        geom.porch = PorchSpec(
            width_ft=porch_width,
            depth_ft=9.0,
            offset_ft=(geom.main_width_ft - porch_width) / 2.0,
        )
    geom.notes.append("Wider garage apron and deep porch create North American craftsman heft.")
    return geom


def _picaresque_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    min_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level
    offset = geom.garage.depth_ft if geom.garage else 0.0

    wing_width = min(max(geom.main_width_ft * 0.36, 15.0), geom.main_width_ft / 1.9)
    wing_depth = geom.main_depth_ft * 0.52
    wing_x = max(1.0, geom.main_width_ft * 0.12)
    wing_y = offset + geom.main_depth_ft * 0.28
    geom.wings.append(
        WingSpec(
            key="picaresque_gallery",
            label="Storybook gallery wing",
            x_ft=wing_x,
            y_ft=wing_y,
            width_ft=wing_width,
            depth_ft=wing_depth,
            min_level=min_level,
            max_level=top_level,
        )
    )
    geom.towers.append(
        TowerSpec(
            key="picaresque_turret",
            label="Poetic corner turret",
            center_x_ft=geom.main_width_ft - max(wing_width * 0.25, 3.0),
            center_y_ft=offset + geom.main_depth_ft * 0.68,
            radius_ft=max(geom.main_width_ft * 0.1, 2.8),
            base_level=min_level,
            top_level=top_level,
            height_scale=1.22,
            segments=14,
            roof_height_ft=base.roof_height_ft * 1.4,
        )
    )
    geom.notes.append("Gallery wing and turret layer in the jagged, storybook cues from the prompt.")
    return geom


def _buttress_variant(config: PromptConfig, base: Geometry) -> Geometry:
    geom = clone_geometry(base)
    base_level = 1 if config.has_basement else 0
    top_level = geom.floors[-1].level
    front_offset = geom.garage.depth_ft if geom.garage else 0.0

    buttress_width = max(geom.main_width_ft * 0.06, 2.2)
    buttress_depth = max(geom.main_depth_ft * 0.24, 6.2)
    bridge_length = max(geom.main_width_ft * 0.14, 4.0)
    bridge_height = max(geom.roof_height_ft * 0.22, 1.4)

    y_positions = [
        front_offset + geom.main_depth_ft * 0.3,
        front_offset + geom.main_depth_ft * 0.68,
    ]
    for idx, y_center in enumerate(y_positions):
        base_y = max(0.0, y_center - buttress_depth / 2.0)
        geom.buttresses.append(
            ButtressSpec(
                key=f"buttress_left_{idx}",
                label="Flying buttress (west span)",
                base_x_ft=-buttress_width * 0.85,
                base_y_ft=base_y,
                width_ft=buttress_width,
                depth_ft=buttress_depth,
                base_level=base_level,
                top_level=top_level,
                direction="x+",
                flying=True,
                bridge_length_ft=bridge_length,
                bridge_height_ft=bridge_height,
            )
        )
        geom.buttresses.append(
            ButtressSpec(
                key=f"buttress_right_{idx}",
                label="Flying buttress (east span)",
                base_x_ft=geom.main_width_ft - buttress_width * 0.15,
                base_y_ft=base_y,
                width_ft=buttress_width,
                depth_ft=buttress_depth,
                base_level=base_level,
                top_level=top_level,
                direction="x-",
                flying=True,
                bridge_length_ft=bridge_length,
                bridge_height_ft=bridge_height,
            )
        )

    rear_depth = max(buttress_depth * 0.75, 5.0)
    rear_width = max(buttress_width * 0.85, 2.0)
    rear_base = front_offset + geom.main_depth_ft - rear_depth * 0.6
    geom.buttresses.append(
        ButtressSpec(
            key="buttress_rear",
            label="Flying buttress (garden span)",
            base_x_ft=(geom.main_width_ft - rear_width) / 2.0,
            base_y_ft=rear_base,
            width_ft=rear_width,
            depth_ft=rear_depth,
            base_level=base_level,
            top_level=top_level,
            direction="y+",
            flying=True,
            bridge_length_ft=max(bridge_length * 0.8, 3.5),
            bridge_height_ft=bridge_height,
        )
    )

    front_depth = max(buttress_depth * 0.58, 4.5)
    front_base = max(0.0, front_offset - front_depth * 0.8)
    geom.buttresses.append(
        ButtressSpec(
            key="buttress_front",
            label="Flying buttress (entry span)",
            base_x_ft=(geom.main_width_ft - rear_width) / 2.0,
            base_y_ft=front_base,
            width_ft=rear_width,
            depth_ft=front_depth,
            base_level=base_level,
            top_level=top_level,
            direction="y-",
            flying=True,
            bridge_length_ft=max(bridge_length * 0.75, 3.2),
            bridge_height_ft=bridge_height,
        )
    )

    geom.notes.append(
        "Flying buttress array braces the main halls for legendary, engineering-first theatrics."
    )
    return geom


def _style_variants(config: PromptConfig, base: Geometry) -> list[CatalogVariant]:
    variants: list[CatalogVariant] = []
    tags = {tag.lower() for tag in config.style_tags}
    if tags & {"scottish", "irish"}:
        variants.append(
            CatalogVariant(
                key="highland_keep",
                label="Highland keep",
                description="Adds a stone tower and chimney mass referencing Scottish and Irish estates.",
                adjust=_highland_keep_variant,
            )
        )
    if "scandinavian" in tags:
        variants.append(
            CatalogVariant(
                key="fjordlight",
                label="Fjordlight pavilion",
                description="Introduces a light pavilion wing and taller ridge suited to Nordic daylighting.",
                adjust=_fjordlight_variant,
            )
        )
    if "dutch" in tags:
        variants.append(
            CatalogVariant(
                key="canal_step",
                label="Canal stepped gables",
                description="Stacks twin stepped gables across the frontage to echo Dutch canal houses.",
                adjust=_canal_step_variant,
            )
        )
    if tags & {"canadian", "american"}:
        variants.append(
            CatalogVariant(
                key="northwoods",
                label="Northwoods porch",
                description="Widens the garage bay and deepens porches for Canadian/American suburban massing.",
                adjust=_northwoods_variant,
            )
        )
    if tags & {"picaresque", "poetic"}:
        variants.append(
            CatalogVariant(
                key="picaresque",
                label="Picaresque turret",
                description="Layers in asymmetrical wings and a turret for jagged, storybook silhouettes.",
                adjust=_picaresque_variant,
            )
        )
    if tags & {"buttress", "legendary", "engineering"}:
        variants.append(
            CatalogVariant(
                key="buttress",
                label="Flying buttress array",
                description="Wraps the main volume with legendary flying buttresses for engineered drama.",
                adjust=_buttress_variant,
            )
        )
    return variants


def default_catalog_variants(config: PromptConfig, base: Geometry) -> list[CatalogVariant]:
    variants = [
        CatalogVariant(
            key="standard",
            label="Baseline massing",
            description="Direct translation of the descriptive prompt into a printable stack.",
            adjust=_baseline_variant,
        ),
        CatalogVariant(
            key="manor",
            label="Manor wing expansion",
            description="Adds a rear entertaining wing and deep porch for estate-style layouts.",
            adjust=_manor_variant,
        ),
        CatalogVariant(
            key="courtyard",
            label="Courtyard terrace",
            description="Mirrored wings carve out a sheltered garden court behind the main house.",
            adjust=_courtyard_variant,
        ),
        CatalogVariant(
            key="gothic",
            label="Gothic spire",
            description="Introduces a front spire and taller ridgeline for cathedral energy.",
            adjust=_gothic_variant,
        ),
        CatalogVariant(
            key="compact",
            label="Compact infill",
            description="Tightens the footprint while keeping the programme intact for urban lots.",
            adjust=_compact_variant,
        ),
        CatalogVariant(
            key="spire",
            label="Skyline atrium",
            description="Raises a central atrium spire for high-rise-inspired silhouettes.",
            adjust=_spire_variant,
        ),
    ]
    variants.extend(_style_variants(config, base))
    return variants


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a minimal STL stack (basement + floors + roof) using heuristics "
            "derived from a descriptive prompt."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Destination Auto3D workspace (default: Auto3D-Render-to-STL)",
    )
    parser.add_argument(
        "--prompt",
        help="Inline prompt describing the house. Mutually exclusive with --prompt-file.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a text file containing the prompt.",
    )
    parser.add_argument(
        "--hero",
        type=Path,
        help="Optional hero render to copy into input_images for reference.",
    )
    parser.add_argument(
        "--model-scale",
        type=float,
        default=DEFAULT_MODEL_SCALE,
        help="Real-to-model scale denominator (default: 100 for 1:100).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite scaffolded files if they already exist.",
    )
    parser.add_argument(
        "--protocol",
        default=DEFAULT_PROTOCOL,
        help="Optional protocol tag recorded in the metadata report.",
    )
    parser.add_argument(
        "--roof",
        dest="roof",
        action="store_true",
        help="Include a simple gable roof STL (default).",
    )
    parser.add_argument(
        "--no-roof",
        dest="roof",
        action="store_false",
        help="Skip generating a roof STL.",
    )
    parser.set_defaults(roof=True)
    return parser.parse_args()


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        raise SystemExit("Provide only --prompt or --prompt-file, not both.")
    if args.prompt:
        return args.prompt.strip()
    if args.prompt_file:
        path = args.prompt_file.expanduser()
        if not path.exists():
            raise SystemExit(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    raise SystemExit("A prompt is required (use --prompt or --prompt-file).")


def extract_prompt_config(text: str) -> PromptConfig:
    lowered = text.lower()

    def search_number(pattern: str) -> float | None:
        match = re.search(pattern, lowered)
        if not match:
            return None
        value = match.group(1)
        try:
            return float(value)
        except ValueError:
            return None

    bedrooms = search_number(r"(\d+(?:\.\d+)?)\s*(?:bed|bedroom)")
    bathrooms = search_number(r"(\d+(?:\.\d+)?)\s*(?:bath|bathroom)")
    floors = search_number(r"(\d+(?:\.\d+)?)\s*(?:floor|storey|story)")
    square_feet = search_number(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft|square\s*feet|sf)")

    has_basement = "basement" in lowered
    style_tag_candidates = {
        "light brown wood": {"light brown", "wood", "timber"},
        "dark oak": {"dark oak", "oak", "timber"},
        "charcoal stone": {"charcoal stone", "stone base", "masonry"},
        "garage": {"garage"},
        "scottish": {"scottish", "highland"},
        "irish": {"irish"},
        "dutch": {"dutch"},
        "scandinavian": {"scandinavian", "nordic"},
        "canadian": {"canadian"},
        "american": {"american"},
        "picaresque": {"picaresque", "picturesque"},
        "poetic": {"poetic", "romantic"},
        "buttress": {"buttress", "buttresses", "flying buttress", "flying buttresses", "vandited"},
        "legendary": {"legendary", "legendary engineering", "legendary features"},
        "engineering": {"engineering", "engineering probability"},
    }
    style_tags = [
        tag
        for tag, needles in style_tag_candidates.items()
        if any(needle in lowered for needle in needles)
    ]

    return PromptConfig(
        bedrooms=max(1, int(round(bedrooms))) if bedrooms else 3,
        bathrooms=bathrooms if bathrooms else 2.0,
        floors_above=max(1, int(round(floors))) if floors else 2,
        has_basement=has_basement,
        declared_square_feet=square_feet,
        style_tags=style_tags,
    )


def estimate_geometry(config: PromptConfig) -> Geometry:
    floors = config.floors_above
    declared = config.declared_square_feet
    bedrooms = config.bedrooms
    bathrooms = config.bathrooms

    bedroom_area = bedrooms * 140.0
    bathroom_area = bathrooms * 55.0
    shared_space = 900.0 + max(0, bedrooms - 3) * 80.0

    total_above = declared if declared else bedroom_area + bathroom_area + shared_space
    per_floor = max(total_above / floors, 650.0)

    ratio_adjust = 1.0
    if "scandinavian" in config.style_tags or "dutch" in config.style_tags:
        ratio_adjust *= 1.08
    if "irish" in config.style_tags or "scottish" in config.style_tags:
        ratio_adjust *= 0.94

    width_depth_ratio = 1.45 * ratio_adjust
    width_ft = math.sqrt(per_floor * width_depth_ratio)
    depth_ft = per_floor / width_ft

    base_height_ft = 8.0
    main_height_ft = 9.0
    upper_height_ft = 8.5
    roof_height_ft = 6.5
    if "scandinavian" in config.style_tags:
        roof_height_ft += 1.0
    if "dutch" in config.style_tags:
        roof_height_ft += 0.6

    specs: list[FloorSpec] = []
    index = 0
    if config.has_basement:
        specs.append(
            FloorSpec(
                key=f"{index:02d}_basement",
                label="Unfinished Basement",
                height_m=base_height_ft * FEET_TO_METERS,
                area_sqft=per_floor,
                level=index,
            )
        )
        index += 1

    specs.append(
        FloorSpec(
            key=f"{index:02d}_main",
            label="Main Floor",
            height_m=main_height_ft * FEET_TO_METERS,
            area_sqft=per_floor,
            level=index,
        )
    )
    index += 1

    for level in range(1, floors):
        specs.append(
            FloorSpec(
                key=f"{index:02d}_upper{level}",
                label=f"Upper Floor {level}",
                height_m=upper_height_ft * FEET_TO_METERS,
                area_sqft=per_floor,
                level=index,
            )
        )
        index += 1

    garage_width_ft = width_ft * 0.42
    garage_width_ft = min(garage_width_ft, width_ft - 6.0)
    garage_width_ft = max(garage_width_ft, 0.0)
    garage_depth_ft = depth_ft * 0.55
    garage_offset_ft = width_ft - garage_width_ft - 3.0
    if garage_offset_ft < 2.0:
        garage_offset_ft = 2.0
        garage_width_ft = max(width_ft - garage_offset_ft - 3.0, 0.0)
    garage = None
    if garage_width_ft >= 10.0 and garage_depth_ft >= 12.0:
        garage = GarageSpec(width_ft=garage_width_ft, depth_ft=garage_depth_ft, offset_ft=garage_offset_ft)

    porch = None
    porch_depth_ft = min(8.0, depth_ft * 0.35)
    porch_width_ft = width_ft * 0.65
    porch_offset_ft = (width_ft - porch_width_ft) / 2.0
    if porch_width_ft > 6.0:
        porch = PorchSpec(width_ft=porch_width_ft, depth_ft=porch_depth_ft, offset_ft=porch_offset_ft)

    chimney = ChimneySpec(
        width_ft=2.6,
        depth_ft=2.1,
        offset_ft=max(width_ft * 0.18, 2.0),
        depth_offset_ft=(garage.depth_ft if garage else 0.0) + depth_ft * 0.62,
    )

    notes = [
        "L-shaped main volume with offset garage wing and upper-floor setback.",
        "Central dormer and chimney keep the roofline articulated even without a hero rear view.",
    ]

    return Geometry(
        main_width_ft=width_ft,
        main_depth_ft=depth_ft,
        floors=specs,
        roof_height_ft=roof_height_ft,
        garage=garage,
        porch=porch,
        chimney=chimney,
        wings=[],
        towers=[],
        buttresses=[],
        notes=notes,
    )


def ft_to_model_mm(value_ft: float, *, scale: float) -> float:
    return value_ft * FEET_TO_METERS * 1000.0 / scale


def convert_to_model_dims(geometry: Geometry, *, scale: float) -> ModelDimensions:
    width_mm = ft_to_model_mm(geometry.width_ft, scale=scale)
    depth_mm = ft_to_model_mm(geometry.total_depth_ft, scale=scale)

    heights_mm = [floor.height_m * 1000.0 / scale for floor in geometry.floors]
    roof_mm = ft_to_model_mm(geometry.roof_height_ft, scale=scale)

    return ModelDimensions(
        width_mm=width_mm,
        depth_mm=depth_mm,
        floor_heights_mm=heights_mm,
        roof_height_mm=roof_mm,
        scale=scale,
    )


def ensure_workspace(base: Path, *, force: bool) -> None:
    base = base.expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    create_project(base, force=force)


def copy_hero(hero: Path | None, workspace: Path) -> Path | None:
    if not hero:
        return None
    source = hero.expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Hero image not found: {source}")
    target_dir = workspace / "input_images"
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / ("hero" + source.suffix.lower())
    import shutil

    shutil.copy2(source, destination)
    print(f"[hero] Copied {source} -> {destination}")
    return destination


def box_triangles(width: float, depth: float, height: float, *, z0: float = 0.0, x0: float = 0.0, y0: float = 0.0) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    x1 = x0 + width
    y1 = y0 + depth
    z1 = z0 + height

    p000 = (x0, y0, z0)
    p100 = (x1, y0, z0)
    p110 = (x1, y1, z0)
    p010 = (x0, y1, z0)
    p001 = (x0, y0, z1)
    p101 = (x1, y0, z1)
    p111 = (x1, y1, z1)
    p011 = (x0, y1, z1)

    return [
        # bottom (-z)
        (p000, p010, p110),
        (p000, p110, p100),
        # top (+z)
        (p001, p101, p111),
        (p001, p111, p011),
        # front (y = y0)
        (p000, p100, p101),
        (p000, p101, p001),
        # back (y = y1)
        (p010, p011, p111),
        (p010, p111, p110),
        # left (x = x0)
        (p000, p001, p011),
        (p000, p011, p010),
        # right (x = x1)
        (p100, p110, p111),
        (p100, p111, p101),
    ]


def gable_roof_triangles(
    width: float,
    depth: float,
    height: float,
    *,
    base_z: float,
    y_offset: float = 0.0,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    x0 = 0.0
    x1 = width
    y0 = y_offset
    y1 = y_offset + depth
    xm = (x0 + x1) / 2.0
    z0 = base_z
    z_peak = base_z + height

    front_left = (x0, y0, z0)
    front_right = (x1, y0, z0)
    back_left = (x0, y1, z0)
    back_right = (x1, y1, z0)
    ridge_front = (xm, y0, z_peak)
    ridge_back = (xm, y1, z_peak)

    return [
        # base (-z)
        (front_left, back_right, front_right),
        (front_left, back_left, back_right),
        # front gable face
        (front_left, front_right, ridge_front),
        # back gable face
        (back_left, ridge_back, back_right),
        # left slope
        (front_left, back_left, ridge_back),
        (front_left, ridge_back, ridge_front),
        # right slope
        (front_right, ridge_front, ridge_back),
        (front_right, ridge_back, back_right),
    ]


def offset_triangles(
    triangles: Iterable[Sequence[Sequence[float]]],
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    shifted: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for triangle in triangles:
        shifted.append(
            tuple((vx + dx, vy + dy, vz + dz) for (vx, vy, vz) in triangle)  # type: ignore[misc]
        )
    return shifted





def regular_polygon_points(sides: int, radius: float, *, center: tuple[float, float] = (0.0, 0.0)) -> list[tuple[float, float]]:
    cx, cy = center
    points: list[tuple[float, float]] = []
    for idx in range(sides):
        angle = (2.0 * math.pi * idx) / sides
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def cone_triangles(
    center_x: float,
    center_y: float,
    radius: float,
    height: float,
    *,
    base_z: float,
    segments: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    base_points_2d = regular_polygon_points(segments, radius, center=(center_x, center_y))
    base_points = [(x, y, base_z) for (x, y) in base_points_2d]
    apex = (center_x, center_y, base_z + height)

    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for idx in range(len(base_points)):
        p1 = base_points[idx]
        p2 = base_points[(idx + 1) % len(base_points)]
        triangles.append((p1, p2, apex))

    for idx in range(1, len(base_points) - 1):
        triangles.append((base_points[0], base_points[idx], base_points[idx + 1]))
    return triangles


def triangle_normal(triangle: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = triangle
    u = (x2 - x1, y2 - y1, z2 - z1)
    v = (x3 - x1, y3 - y1, z3 - z1)
    nx = u[1] * v[2] - u[2] * v[1]
    ny = u[2] * v[0] - u[0] * v[2]
    nz = u[0] * v[1] - u[1] * v[0]
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def polygon_area(points: Sequence[Sequence[float]]) -> float:
    area = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def dedupe_points(points: Sequence[Sequence[float]], eps: float = 1e-6) -> list[tuple[float, float]]:
    unique: list[tuple[float, float]] = []
    for x, y in points:
        if unique and abs(unique[-1][0] - x) < eps and abs(unique[-1][1] - y) < eps:
            continue
        unique.append((x, y))
    if len(unique) >= 2 and abs(unique[0][0] - unique[-1][0]) < eps and abs(unique[0][1] - unique[-1][1]) < eps:
        unique.pop()
    return unique


def ensure_ccw(points: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
    cleaned = dedupe_points(points)
    if polygon_area(cleaned) < 0:
        cleaned.reverse()
    return cleaned


def is_convex(prev_pt: Sequence[float], curr_pt: Sequence[float], next_pt: Sequence[float]) -> bool:
    ax, ay = prev_pt
    bx, by = curr_pt
    cx, cy = next_pt
    cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return cross > 0


def point_in_triangle(pt: Sequence[float], tri: Sequence[Sequence[float]], eps: float = 1e-9) -> bool:
    def sign(p1: Sequence[float], p2: Sequence[float], p3: Sequence[float]) -> float:
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = sign(pt, tri[0], tri[1])
    d2 = sign(pt, tri[1], tri[2])
    d3 = sign(pt, tri[2], tri[0])
    has_neg = (d1 < -eps) or (d2 < -eps) or (d3 < -eps)
    has_pos = (d1 > eps) or (d2 > eps) or (d3 > eps)
    return not (has_neg and has_pos)


def triangulate_polygon(
    points: Sequence[Sequence[float]],
) -> list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]:
    pts = ensure_ccw(points)
    if len(pts) < 3:
        raise ValueError("Polygon requires at least three points")

    vertices = list(range(len(pts)))
    triangles: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = []

    guard = 0
    while len(vertices) > 3:
        guard += 1
        if guard > 1000:
            raise RuntimeError("Failed to triangulate polygon; is it simple?")
        ear_found = False
        for idx in range(len(vertices)):
            prev_idx = vertices[(idx - 1) % len(vertices)]
            curr_idx = vertices[idx]
            next_idx = vertices[(idx + 1) % len(vertices)]

            a = pts[prev_idx]
            b = pts[curr_idx]
            c = pts[next_idx]
            if not is_convex(a, b, c):
                continue

            tri = (a, b, c)
            if any(
                point_in_triangle(pts[other_idx], tri)
                for other_idx in vertices
                if other_idx not in {prev_idx, curr_idx, next_idx}
            ):
                continue

            triangles.append(tri)
            del vertices[idx]
            ear_found = True
            break

        if not ear_found:
            raise RuntimeError("Could not find an ear to clip; polygon may be self-intersecting")

    if len(vertices) == 3:
        triangles.append((pts[vertices[0]], pts[vertices[1]], pts[vertices[2]]))

    return list(triangles)


def extrude_polygon(points: Sequence[Sequence[float]], height: float, *, base_z: float = 0.0) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    pts = ensure_ccw(points)
    tris_2d = triangulate_polygon(pts)
    top_z = base_z + height

    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    for tri in tris_2d:
        bottom = [(x, y, base_z) for (x, y) in reversed(tri)]
        top = [(x, y, top_z) for (x, y) in tri]
        triangles.append(tuple(bottom))
        triangles.append(tuple(top))

    for idx in range(len(pts)):
        p1 = pts[idx]
        p2 = pts[(idx + 1) % len(pts)]
        v1 = (p1[0], p1[1], base_z)
        v2 = (p2[0], p2[1], base_z)
        v3 = (p2[0], p2[1], top_z)
        v4 = (p1[0], p1[1], top_z)
        triangles.append((v1, v2, v3))
        triangles.append((v1, v3, v4))

    return triangles


def write_ascii_stl(path: Path, name: str, triangles: Iterable[Sequence[Sequence[float]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"solid {name}\n")
        for triangle in triangles:
            nx, ny, nz = triangle_normal(triangle)
            handle.write(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n")
            handle.write("    outer loop\n")
            for vertex in triangle:
                vx, vy, vz = vertex
                handle.write(f"      vertex {vx:.6f} {vy:.6f} {vz:.6f}\n")
            handle.write("    endloop\n")
            handle.write("  endfacet\n")
        handle.write(f"endsolid {name}\n")
    print(f"[stl] Wrote {path}")


def base_floor_polygon_ft(
    geometry: Geometry,
    *,
    include_garage: bool,
    include_setback: bool,
) -> list[tuple[float, float]]:
    width = geometry.main_width_ft
    main_depth = geometry.main_depth_ft

    garage_depth = geometry.garage.depth_ft if include_garage and geometry.garage else 0.0
    garage_offset = geometry.garage.offset_ft if include_garage and geometry.garage else 0.0
    garage_width = geometry.garage.width_ft if include_garage and geometry.garage else 0.0

    side_margin = 0.0
    back_margin = 0.0
    front_margin = 0.0

    if include_setback:
        side_margin = min(width * 0.08, 1.5)
        back_margin = min(main_depth * 0.08, 1.4)
        front_margin = min(main_depth * 0.05, 0.9)
        include_garage = False
        garage_depth = 0.0

    x0 = side_margin
    x1 = width - side_margin
    y_front_main = garage_depth + front_margin
    y_back = garage_depth + main_depth - back_margin

    polygon: list[tuple[float, float]] = [
        (x0, y_front_main),
        (x0, y_back),
        (x1, y_back),
        (x1, y_front_main),
    ]

    if include_garage and geometry.garage:
        g0 = garage_offset
        g1 = garage_offset + garage_width
        polygon.extend(
            [
                (g1, y_front_main),
                (g1, 0.0),
                (g0, 0.0),
                (g0, y_front_main),
            ]
        )

    return polygon


def floor_polygons_ft(geometry: Geometry, spec: FloorSpec) -> list[list[tuple[float, float]]]:
    include_garage = geometry.garage is not None and spec.label in {
        "Unfinished Basement",
        "Main Floor",
    }
    include_setback = spec.label.startswith("Upper")

    polygons = [
        base_floor_polygon_ft(
            geometry,
            include_garage=include_garage,
            include_setback=include_setback,
        )
    ]

    if geometry.porch and spec.label == "Main Floor":
        porch_depth = min(
            geometry.porch.depth_ft,
            geometry.garage.depth_ft * 0.85 if geometry.garage else geometry.porch.depth_ft,
        )
        porch_poly = [
            (geometry.porch.offset_ft, 0.0),
            (geometry.porch.offset_ft, porch_depth),
            (geometry.porch.offset_ft + geometry.porch.width_ft, porch_depth),
            (geometry.porch.offset_ft + geometry.porch.width_ft, 0.0),
        ]
        polygons.append(porch_poly)

    return polygons


def polygons_ft_to_mm(polygons: Sequence[Sequence[tuple[float, float]]], *, scale: float) -> list[list[tuple[float, float]]]:
    converted: list[list[tuple[float, float]]] = []
    for polygon in polygons:
        converted.append([(ft_to_model_mm(x, scale=scale), ft_to_model_mm(y, scale=scale)) for (x, y) in polygon])
    return converted


def floor_triangles(
    geometry: Geometry,
    spec: FloorSpec,
    height_mm: float,
    *,
    scale: float,
    base_z: float = 0.0,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    polygons = floor_polygons_ft(geometry, spec)
    polygons_mm = polygons_ft_to_mm(polygons, scale=scale)
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for polygon in polygons_mm:
        triangles.extend(extrude_polygon(polygon, height_mm, base_z=base_z))

    for wing in geometry.wings:
        if wing.min_level <= spec.level <= wing.max_level:
            wing_poly = [
                (wing.x_ft, wing.y_ft),
                (wing.x_ft + wing.width_ft, wing.y_ft),
                (wing.x_ft + wing.width_ft, wing.y_ft + wing.depth_ft),
                (wing.x_ft, wing.y_ft + wing.depth_ft),
            ]
            wing_mm = polygons_ft_to_mm([wing_poly], scale=scale)[0]
            triangles.extend(extrude_polygon(wing_mm, height_mm, base_z=base_z))

    for tower in geometry.towers:
        if tower.base_level <= spec.level <= tower.top_level:
            radius_mm = ft_to_model_mm(tower.radius_ft, scale=scale)
            center_x_mm = ft_to_model_mm(tower.center_x_ft, scale=scale)
            center_y_mm = ft_to_model_mm(tower.center_y_ft, scale=scale)
            tower_points = regular_polygon_points(
                max(6, tower.segments), radius_mm, center=(center_x_mm, center_y_mm)
            )
            tower_tris = extrude_polygon(tower_points, height_mm * tower.height_scale, base_z=base_z)
            triangles.extend(tower_tris)

    for buttress in geometry.buttresses:
        if buttress.base_level <= spec.level <= buttress.top_level:
            width_mm = ft_to_model_mm(buttress.width_ft, scale=scale)
            depth_mm = ft_to_model_mm(buttress.depth_ft, scale=scale)
            base_x_mm = ft_to_model_mm(buttress.base_x_ft, scale=scale)
            base_y_mm = ft_to_model_mm(buttress.base_y_ft, scale=scale)
            triangles.extend(
                box_triangles(
                    width_mm,
                    depth_mm,
                    height_mm,
                    x0=base_x_mm,
                    y0=base_y_mm,
                    z0=base_z,
                )
            )
    return triangles


def build_roof_triangles(geometry: Geometry, model_dims: ModelDimensions) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    base_z = sum(model_dims.floor_heights_mm)
    width_mm = ft_to_model_mm(geometry.main_width_ft, scale=model_dims.scale)
    main_depth_mm = ft_to_model_mm(geometry.main_depth_ft, scale=model_dims.scale)
    garage_depth_mm = (
        ft_to_model_mm(geometry.garage.depth_ft, scale=model_dims.scale)
        if geometry.garage
        else 0.0
    )

    level_bases: dict[int, float] = {}
    level_tops: dict[int, float] = {}
    cumulative = 0.0
    for spec, height in zip(geometry.floors, model_dims.floor_heights_mm):
        level_bases[spec.level] = cumulative
        cumulative += height
        level_tops[spec.level] = cumulative

    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    triangles.extend(
        gable_roof_triangles(
            width_mm,
            main_depth_mm,
            model_dims.roof_height_mm,
            base_z=base_z,
            y_offset=garage_depth_mm,
        )
    )

    if geometry.garage:
        garage_width_mm = ft_to_model_mm(geometry.garage.width_ft, scale=model_dims.scale)
        garage_offset_mm = ft_to_model_mm(geometry.garage.offset_ft, scale=model_dims.scale)
        garage_height_mm = model_dims.roof_height_mm * 0.55
        garage_base_z = base_z - model_dims.roof_height_mm * 0.4
        garage_triangles = gable_roof_triangles(
            garage_width_mm,
            garage_depth_mm,
            garage_height_mm,
            base_z=garage_base_z,
            y_offset=0.0,
        )
        triangles.extend(offset_triangles(garage_triangles, dx=garage_offset_mm))

    dormer_width_ft = min(geometry.main_width_ft * 0.3, 12.0)
    dormer_depth_ft = min(geometry.main_depth_ft * 0.35, 9.0)
    dormer_width_mm = ft_to_model_mm(dormer_width_ft, scale=model_dims.scale)
    dormer_depth_mm = ft_to_model_mm(dormer_depth_ft, scale=model_dims.scale)
    dormer_body_height = model_dims.roof_height_mm * 0.35
    dormer_base_z = base_z + model_dims.roof_height_mm * 0.12
    dormer_offset_x = ft_to_model_mm((geometry.main_width_ft - dormer_width_ft) / 2.0, scale=model_dims.scale)
    dormer_offset_y = garage_depth_mm + ft_to_model_mm(geometry.main_depth_ft * 0.28, scale=model_dims.scale)
    triangles.extend(
        box_triangles(
            dormer_width_mm,
            dormer_depth_mm * 0.6,
            dormer_body_height,
            x0=dormer_offset_x,
            y0=dormer_offset_y,
            z0=dormer_base_z,
        )
    )
    dormer_roof_height = model_dims.roof_height_mm * 0.4
    dormer_roof = gable_roof_triangles(
        dormer_width_mm,
        dormer_depth_mm * 0.6,
        dormer_roof_height,
        base_z=dormer_base_z + dormer_body_height,
        y_offset=dormer_offset_y,
    )
    triangles.extend(offset_triangles(dormer_roof, dx=dormer_offset_x))

    if geometry.chimney:
        chimney_width_mm = ft_to_model_mm(geometry.chimney.width_ft, scale=model_dims.scale)
        chimney_depth_mm = ft_to_model_mm(geometry.chimney.depth_ft, scale=model_dims.scale)
        chimney_offset_x = ft_to_model_mm(geometry.chimney.offset_ft, scale=model_dims.scale)
        chimney_offset_y = ft_to_model_mm(geometry.chimney.depth_offset_ft, scale=model_dims.scale)
        chimney_height_mm = model_dims.roof_height_mm * 0.75
        chimney_base_z = base_z + model_dims.roof_height_mm * 0.3
        triangles.extend(
            box_triangles(
                chimney_width_mm,
                chimney_depth_mm,
                chimney_height_mm,
                x0=chimney_offset_x,
                y0=chimney_offset_y,
                z0=chimney_base_z,
            )
        )

    for tower in geometry.towers:
        radius_mm = ft_to_model_mm(tower.radius_ft, scale=model_dims.scale)
        center_x_mm = ft_to_model_mm(tower.center_x_ft, scale=model_dims.scale)
        center_y_mm = ft_to_model_mm(tower.center_y_ft, scale=model_dims.scale)
        top_level = min(tower.top_level, max(level_tops.keys(), default=0))
        tower_base_z = level_tops.get(top_level, base_z)
        roof_height_ft = tower.roof_height_ft if tower.roof_height_ft is not None else geometry.roof_height_ft * 0.9
        roof_height_mm = ft_to_model_mm(roof_height_ft, scale=model_dims.scale)
        triangles.extend(
            cone_triangles(
                center_x_mm,
                center_y_mm,
                radius_mm * 1.05,
                roof_height_mm,
                base_z=tower_base_z,
                segments=max(6, tower.segments),
            )
        )

    for buttress in geometry.buttresses:
        if not buttress.flying or buttress.bridge_length_ft <= 0.0:
            continue
        top_level = min(buttress.top_level, max(level_tops.keys(), default=0))
        buttress_top_z = level_tops.get(top_level, base_z)
        width_mm = ft_to_model_mm(buttress.width_ft, scale=model_dims.scale)
        depth_mm = ft_to_model_mm(buttress.depth_ft, scale=model_dims.scale)
        base_x_mm = ft_to_model_mm(buttress.base_x_ft, scale=model_dims.scale)
        base_y_mm = ft_to_model_mm(buttress.base_y_ft, scale=model_dims.scale)
        bridge_height_mm = ft_to_model_mm(max(buttress.bridge_height_ft, 0.1), scale=model_dims.scale)
        length_mm = ft_to_model_mm(max(buttress.bridge_length_ft, 0.0), scale=model_dims.scale)
        if length_mm <= 0.0:
            continue
        z0 = buttress_top_z - bridge_height_mm * 0.3
        if buttress.direction == "x+":
            x0 = base_x_mm + width_mm
            y0 = base_y_mm + depth_mm * 0.2
            triangles.extend(
                box_triangles(
                    length_mm,
                    depth_mm * 0.6,
                    bridge_height_mm,
                    x0=x0,
                    y0=y0,
                    z0=z0,
                )
            )
        elif buttress.direction == "x-":
            x0 = base_x_mm - length_mm
            y0 = base_y_mm + depth_mm * 0.2
            triangles.extend(
                box_triangles(
                    length_mm,
                    depth_mm * 0.6,
                    bridge_height_mm,
                    x0=x0,
                    y0=y0,
                    z0=z0,
                )
            )
        elif buttress.direction == "y+":
            x0 = base_x_mm + width_mm * 0.2
            y0 = base_y_mm + depth_mm
            triangles.extend(
                box_triangles(
                    width_mm * 0.6,
                    length_mm,
                    bridge_height_mm,
                    x0=x0,
                    y0=y0,
                    z0=z0,
                )
            )
        elif buttress.direction == "y-":
            x0 = base_x_mm + width_mm * 0.2
            y0 = base_y_mm - length_mm
            triangles.extend(
                box_triangles(
                    width_mm * 0.6,
                    length_mm,
                    bridge_height_mm,
                    x0=x0,
                    y0=y0,
                    z0=z0,
                )
            )

    return triangles


def generate_floor_stls(
    workspace: Path,
    geometry: Geometry,
    model_dims: ModelDimensions,
    *,
    destination: Path | None = None,
    prefix: str = "",
) -> list[Path]:
    outputs = destination or (workspace / "outputs")
    outputs.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    for spec, height_mm in zip(geometry.floors, model_dims.floor_heights_mm):
        triangles = floor_triangles(geometry, spec, height_mm, scale=model_dims.scale, base_z=0.0)
        filename = f"{prefix}floor_{spec.key}.stl"
        path = outputs / filename
        write_ascii_stl(path, spec.key, triangles)
        exported.append(path)
    return exported


def generate_roof_stl(
    workspace: Path,
    geometry: Geometry,
    model_dims: ModelDimensions,
    *,
    destination: Path | None = None,
    name: str = "roof.stl",
) -> Path:
    outputs = destination or (workspace / "outputs")
    triangles = build_roof_triangles(geometry, model_dims)
    path = outputs / name
    write_ascii_stl(path, "roof", triangles)
    return path


def generate_assembled_stl(
    workspace: Path,
    geometry: Geometry,
    model_dims: ModelDimensions,
    *,
    include_roof: bool,
    destination: Path | None = None,
    name: str = "assembled.stl",
) -> Path:
    outputs = destination or (workspace / "outputs")
    triangles: list[Sequence[Sequence[float]]] = []
    z = 0.0
    for spec, height in zip(geometry.floors, model_dims.floor_heights_mm):
        triangles.extend(floor_triangles(geometry, spec, height, scale=model_dims.scale, base_z=z))
        z += height
    if include_roof:
        triangles.extend(build_roof_triangles(geometry, model_dims))
    path = outputs / name
    write_ascii_stl(path, "assembled", triangles)
    return path


def write_catalog_index(
    workspace: Path,
    config: PromptConfig,
    entries: Sequence[tuple[CatalogVariant, Path]],
    *,
    protocol: str,
) -> Path:
    catalog_dir = workspace / "outputs" / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    index = catalog_dir / "_index.md"

    with index.open("w", encoding="utf-8") as handle:
        handle.write("# Auto3D Prompt Catalog\n\n")
        handle.write(f"**Protocol:** {protocol}\n\n")
        handle.write("## Prompt summary\n\n")
        handle.write(f"- Bedrooms: {config.bedrooms}\n")
        handle.write(f"- Bathrooms: {config.bathrooms:.1f}\n")
        handle.write(f"- Floors above grade: {config.floors_above}\n")
        handle.write(f"- Basement: {'yes' if config.has_basement else 'no'}\n\n")

        handle.write("## Variants\n\n")
        for variant, rel_dir in entries:
            handle.write(f"- **{variant.label}** (`{variant.key}`) — {variant.description}\n")
            handle.write(f"  - Assets: {rel_dir.as_posix()}\n")
        handle.write("\n")
    print(f"[catalog] Wrote {index}")
    return index


def generate_catalog(
    workspace: Path,
    prompt: str,
    *,
    model_scale: float,
    include_roof: bool,
    protocol: str,
    force: bool,
    hero: Path | None = None,
    variants: Sequence[CatalogVariant] | None = None,
) -> dict[str, list[Path]]:
    workspace = workspace.expanduser().resolve()
    ensure_workspace(workspace, force=force)
    copy_hero(hero, workspace)

    config = extract_prompt_config(prompt)
    base_geometry = estimate_geometry(config)
    variant_list = list(variants or default_catalog_variants(config, base_geometry))

    catalog_root = workspace / "outputs" / "catalog"
    catalog_root.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, list[Path]] = {}
    index_entries: list[tuple[CatalogVariant, Path]] = []

    for variant in variant_list:
        geometry = variant.adjust(config, base_geometry)
        model_dims = convert_to_model_dims(geometry, scale=model_scale)
        variant_dir = catalog_root / variant.key
        variant_dir.mkdir(parents=True, exist_ok=True)

        variant_paths: list[Path] = []
        variant_paths.extend(
            generate_floor_stls(
                workspace,
                geometry,
                model_dims,
                destination=variant_dir,
            )
        )
        if include_roof:
            variant_paths.append(
                generate_roof_stl(
                    workspace,
                    geometry,
                    model_dims,
                    destination=variant_dir,
                )
            )
        variant_paths.append(
            generate_assembled_stl(
                workspace,
                geometry,
                model_dims,
                include_roof=include_roof,
                destination=variant_dir,
            )
        )
        variant_printability = evaluate_printability(
            [path for path in variant_paths if path.suffix.lower() == ".stl"]
        )
        variant_paths.append(
            write_printability_report(
                variant_dir,
                variant_printability,
                name="printability.md",
            )
        )
        variant_paths.append(
            write_report(
                workspace,
                prompt=prompt,
                config=config,
                geometry=geometry,
                model=model_dims,
                protocol=protocol,
                scale=model_scale,
                destination=variant_dir,
                report_name="report.md",
                variant_label=variant.label,
                variant_description=variant.description,
                printability=variant_printability,
            )
        )
        if not variant_printability.success:
            errors = [
                issue.message for issue in variant_printability.issues if issue.level == "error"
            ]
            raise RuntimeError(
                "Catalog printability gate failed:\n" + "\n".join(f"- {message}" for message in errors)
            )
        outputs[variant.key] = variant_paths
        rel_dir = Path("outputs") / "catalog" / variant.key
        index_entries.append((variant, rel_dir))

    index_path = write_catalog_index(workspace, config, index_entries, protocol=protocol)
    outputs["index"] = [index_path]
    return outputs


def write_report(
    workspace: Path,
    *,
    prompt: str,
    config: PromptConfig,
    geometry: Geometry,
    model: ModelDimensions,
    protocol: str,
    scale: float,
    destination: Path | None = None,
    report_name: str | None = None,
    variant_label: str | None = None,
    variant_description: str | None = None,
    printability: PrintabilityResult | None = None,
) -> Path:
    outputs = destination or (workspace / "outputs")
    outputs.mkdir(parents=True, exist_ok=True)
    report = outputs / (report_name or "auto3d_prompt_report.md")

    width_m = geometry.width_ft * FEET_TO_METERS
    depth_m = geometry.total_depth_ft * FEET_TO_METERS
    total_height_m = sum(floor.height_m for floor in geometry.floors)
    if model.roof_height_mm > 0:
        total_height_m += geometry.roof_height_ft * FEET_TO_METERS

    def line(label: str, meters: float) -> str:
        centimeters = meters * 100.0
        millimeters = meters * 1000.0
        feet = meters / FEET_TO_METERS
        return f"- {label}: {meters:.2f} m | {centimeters:.1f} cm | {millimeters:.1f} mm | {feet:.1f} ft"

    level_lookup = {spec.level: spec.label for spec in geometry.floors}

    def level_name(level: int) -> str:
        return level_lookup.get(level, f"Level {level}")

    with report.open("w", encoding="utf-8") as handle:
        handle.write("# Auto3D Prompt-to-STL Summary\n\n")
        handle.write(f"**Protocol:** {protocol}\n\n")
        handle.write("## Prompt\n\n")
        handle.write(f"> {prompt.strip()}\n\n")
        handle.write("## Parsed Requirements\n\n")
        handle.write(f"- Bedrooms: {config.bedrooms}\n")
        handle.write(f"- Bathrooms: {config.bathrooms:.1f}\n")
        handle.write(f"- Floors above grade: {config.floors_above}\n")
        handle.write(f"- Basement: {'yes' if config.has_basement else 'no'}\n")
        if config.declared_square_feet:
            handle.write(f"- Declared square footage: {config.declared_square_feet:.0f} sq ft\n")
        if config.style_tags:
            handle.write("- Style tags: " + ", ".join(config.style_tags) + "\n")
        handle.write("\n")

        if variant_label:
            handle.write("## Variant\n\n")
            handle.write(f"- Name: {variant_label}\n")
            if variant_description:
                handle.write(f"- Summary: {variant_description}\n")
            handle.write("\n")

        handle.write("## Real-World Dimensions\n\n")
        handle.write(line("Width", width_m) + "\n")
        handle.write(line("Depth", depth_m) + "\n")
        handle.write(line("Total height (including roof)", total_height_m) + "\n\n")

        handle.write(f"## Model Dimensions (at scale 1:{scale:.0f})\n\n")
        handle.write(
            f"- Width: {model.width_mm:.1f} mm\n- Depth: {model.depth_mm:.1f} mm\n"
        )
        for spec, height in zip(geometry.floors, model.floor_heights_mm):
            handle.write(f"- {spec.label}: {height:.1f} mm tall\n")
        if model.roof_height_mm > 0:
            handle.write(f"- Roof: {model.roof_height_mm:.1f} mm tall\n")
        handle.write("\n")

        handle.write("## Generated Massing Features\n\n")
        for note in geometry.notes:
            handle.write(f"- {note}\n")
        if geometry.wings:
            handle.write("- Wings and extensions:\n")
            for wing in geometry.wings:
                handle.write(
                    f"  - {wing.label}: spans {level_name(wing.min_level)} → {level_name(wing.max_level)}, "
                    f"{wing.width_ft:.1f} ft × {wing.depth_ft:.1f} ft footprint.\n"
                )
        if geometry.towers:
            handle.write("- Towers and spires:\n")
            for tower in geometry.towers:
                handle.write(
                    f"  - {tower.label}: radius {tower.radius_ft:.1f} ft rising from {level_name(tower.base_level)} "
                    f"to {level_name(tower.top_level)}.\n"
                )
        if geometry.buttresses:
            handle.write("- Structural buttresses:\n")
            for buttress in geometry.buttresses:
                span = f"{level_name(buttress.base_level)} → {level_name(buttress.top_level)}"
                reach = (
                    f" with flying reach {buttress.bridge_length_ft:.1f} ft"
                    if buttress.flying and buttress.bridge_length_ft > 0
                    else ""
                )
                handle.write(
                    f"  - {buttress.label}: spans {span}, {buttress.width_ft:.1f} ft × {buttress.depth_ft:.1f} ft footprint{reach}.\n"
                )
        if geometry.garage:
            handle.write(line("Garage width", geometry.garage.width_ft * FEET_TO_METERS) + "\n")
            handle.write(line("Garage depth", geometry.garage.depth_ft * FEET_TO_METERS) + "\n")
        if geometry.porch:
            handle.write(line("Porch depth", geometry.porch.depth_ft * FEET_TO_METERS) + "\n")
        dormer_width_ft = min(geometry.main_width_ft * 0.3, 12.0)
        handle.write(line("Central dormer width", dormer_width_ft * FEET_TO_METERS) + "\n")
        if geometry.chimney:
            handle.write(line("Chimney projection", geometry.chimney.depth_ft * FEET_TO_METERS) + "\n")
        handle.write("\n")

        if printability is not None:
            handle.write("## Printability Gate\n\n")
            handle.write(render_printability_markdown(printability, include_header=False))

        capabilities = recommended_capabilities(
            style_tags=config.style_tags,
            floors=config.floors_above,
            has_basement=config.has_basement,
            include_catalog_overview=True,
        )
        if capabilities:
            handle.write("## Recommended AI Capability Stack\n\n")
            for cap in capabilities:
                handle.write(f"- **{cap.label}** [{cap.category}]\n")
                handle.write(f"  - Description: {cap.description}\n")
                if cap.inputs:
                    handle.write(f"  - Inputs: {', '.join(cap.inputs)}\n")
                if cap.outputs:
                    handle.write(f"  - Outputs: {', '.join(cap.outputs)}\n")
                if cap.providers:
                    handle.write(f"  - Providers: {', '.join(cap.providers)}\n")
                availability = "Offline-ready" if cap.offline_ready else "Cloud or dedicated GPU recommended"
                handle.write(f"  - Availability: {availability}\n")
                for note in cap.notes:
                    handle.write(f"    • {note}\n")
            handle.write("\n")

        handle.write("## Output Files\n\n")
        for spec in geometry.floors:
            handle.write(f"- floor_{spec.key}.stl\n")
        if model.roof_height_mm > 0:
            handle.write("- roof.stl\n")
        handle.write("- assembled.stl\n")
    print(f"[report] Wrote {report}")
    return report


def main() -> None:
    args = parse_args()
    prompt = load_prompt(args)
    workspace = args.workspace.expanduser().resolve()
    ensure_workspace(workspace, force=args.force)
    copy_hero(args.hero, workspace)

    config = extract_prompt_config(prompt)
    geometry = estimate_geometry(config)
    model_dims = convert_to_model_dims(geometry, scale=args.model_scale)

    floor_paths = generate_floor_stls(workspace, geometry, model_dims)
    stl_paths = list(floor_paths)
    if args.roof:
        stl_paths.append(generate_roof_stl(workspace, geometry, model_dims))
    stl_paths.append(
        generate_assembled_stl(workspace, geometry, model_dims, include_roof=args.roof)
    )
    printability = evaluate_printability(stl_paths)
    write_printability_report(workspace / "outputs", printability)
    write_report(
        workspace,
        prompt=prompt,
        config=config,
        geometry=geometry,
        model=model_dims,
        protocol=args.protocol,
        scale=args.model_scale,
        printability=printability,
    )
    if not printability.success:
        errors = [issue.message for issue in printability.issues if issue.level == "error"]
        raise SystemExit("Printability gate failed:\n" + "\n".join(f"- {message}" for message in errors))
    print("[done] Prompt-derived STL set generated.")


if __name__ == "__main__":
    main()
