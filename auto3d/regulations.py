"""Regional building code references for Auto3D reporting."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BuildingCodeReference:
    """Reference metadata for a building code or guideline."""

    key: str
    region: str
    name: str
    jurisdiction: str
    description: str
    url: str
    scale_applicability: Sequence[str]
    notes: Sequence[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def matches_keywords(self, keywords: Iterable[str]) -> bool:
        terms = {kw.lower() for kw in keywords}
        if not terms:
            return True
        haystack = " ".join(
            [self.key, self.region, self.name, self.jurisdiction, self.description]
        ).lower()
        return any(term in haystack for term in terms)


_CATALOG: tuple[BuildingCodeReference, ...] = (
    BuildingCodeReference(
        key="ab_building_code_2019",
        region="alberta",
        name="Alberta Building Code 2019",
        jurisdiction="Province of Alberta",
        description=(
            "Primary code adopted under the Safety Codes Act; aligns with the 2015 "
            "National Building Code with Alberta-specific amendments for housing "
            "and small buildings."
        ),
        url="https://www.alberta.ca/building-code.aspx",
        scale_applicability=("toy", "residential", "commercial"),
        notes=(
            "Applies to detached homes, townhouses, and small care occupancies; toy-scale "
            "models should reference spatial clearances when representing egress.",
            "Enforced by accredited municipalities such as Calgary, Edmonton, and Red Deer.",
        ),
    ),
    BuildingCodeReference(
        key="nbc_2020",
        region="canada",
        name="National Building Code of Canada 2020",
        jurisdiction="National Research Council Canada",
        description=(
            "Model code that provinces adopt or adapt; Part 9 covers housing up to three "
            "storeys and 600 m², making it the baseline for residential floor prints."
        ),
        url="https://nrc-publications.canada.ca/eng/view/object/?id=26aa5f71-7b7e-45e6-bc3f-44a8a3c0edba",
        scale_applicability=("toy", "residential", "education"),
        notes=(
            "Use Part 9 for one- and two-family dwellings; Part 3 if the model represents "
            "larger assembly spaces.",
            "Supplement with the National Fire Code when showcasing fire egress or life safety routes.",
        ),
    ),
    BuildingCodeReference(
        key="edmonton_infill_design_guide",
        region="alberta",
        name="Edmonton Infill Design Guidelines",
        jurisdiction="City of Edmonton",
        description=(
            "Urban design guidance for small-scale residential projects, covering massing, "
            "setbacks, garages, and façades in mature neighbourhoods."
        ),
        url="https://www.edmonton.ca/city_government/urban_planning_and_design/infill-design-strategy",
        scale_applicability=("toy", "residential", "urban-design"),
        notes=(
            "Useful when cataloguing variants for Canadian/American style briefs in mature communities.",
            "Pair with the Zoning Bylaw 20001 for lot coverage and height envelopes.",
        ),
    ),
    BuildingCodeReference(
        key="calgary_development_permit",
        region="alberta",
        name="Calgary Residential Development Permit Guide",
        jurisdiction="City of Calgary",
        description=(
            "Step-by-step process for securing residential development permits including "
            "plan requirements, submission checklists, and review timelines."
        ),
        url="https://www.calgary.ca/development/development-permit-residential.html",
        scale_applicability=("residential", "commercial", "education"),
        notes=(
            "Clarifies when garages, secondary suites, or contextual front setbacks trigger additional review.",
            "Helps align Auto3D deliverables (floor plates, sections) with municipal submittal packages.",
        ),
    ),
    BuildingCodeReference(
        key="iecc_2021",
        region="north-america",
        name="International Energy Conservation Code 2021",
        jurisdiction="International Code Council",
        description=(
            "Energy efficiency standards referenced by many Canadian and U.S. jurisdictions "
            "for envelope insulation, glazing ratios, and mechanical baselines."
        ),
        url="https://codes.iccsafe.org/content/IECC2021P2",
        scale_applicability=("residential", "commercial"),
        notes=(
            "Use for sustainability narratives when selling hand-held models to developers or educators.",
            "Coordinate with provincial supplements (e.g., Alberta Energy Code for Houses).",
        ),
    ),
)


def building_code_catalog() -> list[BuildingCodeReference]:
    """Return the full building code catalog."""

    return list(_CATALOG)


def filter_building_codes(
    *,
    regions: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    scales: Sequence[str] | None = None,
) -> list[BuildingCodeReference]:
    """Filter the catalog by region, keywords, and model scale applicability."""

    region_set = {region.lower() for region in regions or ()}
    scale_set = {scale.lower() for scale in scales or ()}
    keywords = keywords or []

    results: list[BuildingCodeReference] = []
    for entry in _CATALOG:
        if region_set and entry.region.lower() not in region_set:
            continue
        if scale_set and not scale_set.intersection(s.lower() for s in entry.scale_applicability):
            continue
        if not entry.matches_keywords(keywords):
            continue
        results.append(entry)
    return results


__all__ = [
    "BuildingCodeReference",
    "building_code_catalog",
    "filter_building_codes",
]
