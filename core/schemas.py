from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Dimension(StrEnum):
    DIET = "diet"
    ALLERGY = "allergy"
    CUISINE = "cuisine"
    INGREDIENT = "ingredient"
    DISH = "dish"
    SPICE = "spice"
    BUDGET = "budget"


class PreferenceChange(StrictModel):
    operation: Literal["set", "remove"]
    dimension: Dimension
    subject: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=100)
    evidence: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_value(self):
        self.subject = normalize(self.subject)
        self.value = normalize(self.value)
        if self.dimension in {Dimension.SPICE, Dimension.BUDGET}:
            self.subject = "default"
        if self.operation == "remove":
            return self
        if self.dimension == Dimension.DIET:
            if self.subject not in {"vegetarian", "vegan"} or self.value != "required":
                raise ValueError("Only confirmed vegetarian/vegan classifications are supported")
        elif self.dimension == Dimension.ALLERGY:
            if self.value != "avoid":
                raise ValueError("An allergy must have value avoid")
        elif self.dimension in {Dimension.CUISINE, Dimension.INGREDIENT, Dimension.DISH}:
            if self.value not in {"like", "dislike"}:
                raise ValueError("Affinity must be like or dislike")
        elif self.dimension == Dimension.SPICE:
            if self.value not in {"0", "1", "2", "3"}:
                raise ValueError("Spice must be 0..3")
        elif self.dimension == Dimension.BUDGET:
            amount = float(self.value)
            if not 0 <= amount <= 100000 or not amount < float("inf"):
                raise ValueError("Invalid budget")
        return self


ConstraintField = Literal[
    "category",
    "max_price",
    "vegetarian",
    "vegan",
    "max_spice",
    "excluded_ingredients",
    "allergens",
    "cuisine",
    "required_ingredients",
    "excluded_dishes",
    "unsupported",
]


class Constraints(StrictModel):
    category: str | None = None
    max_price: float | None = Field(default=None, ge=0, le=100000)
    vegetarian: bool | None = None
    vegan: bool | None = None
    max_spice: int | None = Field(default=None, ge=0, le=3)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=30)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    cuisine: str | None = None
    required_ingredients: list[str] = Field(default_factory=list, max_length=30)
    excluded_dishes: list[str] = Field(default_factory=list, max_length=30)
    unsupported: list[str] = Field(default_factory=list, max_length=30)


class ConstraintPatch(StrictModel):
    """Null leaves a scalar unchanged; lists add entries. Clearing requires clear_fields."""

    category: str | None = None
    max_price: float | None = Field(default=None, ge=0, le=100000)
    vegetarian: bool | None = None
    vegan: bool | None = None
    max_spice: int | None = Field(default=None, ge=0, le=3)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=30)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    cuisine: str | None = None
    required_ingredients: list[str] = Field(default_factory=list, max_length=30)
    excluded_dishes: list[str] = Field(default_factory=list, max_length=30)
    unsupported: list[str] = Field(default_factory=list, max_length=30)
    clear_fields: list[ConstraintField] = Field(default_factory=list)

    @field_validator("vegetarian", "vegan")
    @classmethod
    def only_enable_dietary_requirements(cls, value):
        # False is not evidence that the user removed an active restriction.
        # Explicit removal uses clear_fields; an unused boolean must be a no-op.
        return True if value is True else None


class Extraction(StrictModel):
    """Proposed memory edits and current-request constraints; no conversational routing."""

    changes: list[PreferenceChange] = Field(default_factory=list, max_length=30)
    temporary: ConstraintPatch = Field(default_factory=ConstraintPatch)
    new_request: bool = False
    forget_all: bool = False
    forget_evidence: str = ""


class AssistantResponse(StrictModel):
    reply: str = Field(
        min_length=1,
        max_length=700,
        description="A brief natural reply. Detailed menu facts are rendered separately from selected records.",
    )
    item_ids: list[int] = Field(default_factory=list, max_length=5)


class SearchFilters(Constraints):
    sort_by: Literal["recommended", "price_asc", "price_desc"] = "recommended"
    limit: int = Field(default=10, ge=1, le=50)
    query: str | None = Field(default=None, max_length=200)


def patch_constraints(current: Constraints, extraction: Extraction) -> Constraints:
    data = Constraints().model_dump() if extraction.new_request else current.model_dump()
    defaults = Constraints().model_dump()
    for field in extraction.temporary.clear_fields:
        data[field] = defaults[field]
    for key, value in extraction.temporary.model_dump(exclude={"clear_fields"}).items():
        if isinstance(value, list):
            data[key] = list(
                dict.fromkeys([*data[key], *(normalize(x) for x in value if x.strip())])
            )
        elif value is not None:
            data[key] = value
    return Constraints.model_validate(data)


def effective_constraints(temporary: Constraints, profile: list[dict]) -> Constraints:
    """Numeric request budgets override saved defaults; saved diets/allergies still apply."""
    result = temporary.model_copy(deep=True)
    for pref in profile:
        dim, subject, value = pref["dimension"], pref["subject"], pref["value"]
        if dim == "diet":
            setattr(result, subject, True)
        elif dim == "allergy":
            result.allergens.append(subject)
        elif dim == "budget" and temporary.max_price is None:
            result.max_price = float(value)
    return result
