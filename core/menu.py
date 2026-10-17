from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.schemas import Constraints, SearchFilters, normalize


class Dietary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    vegetarian: bool | None
    vegan: bool | None


class MenuItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: int
    name: str
    ingredients: list[str]
    cuisine: str
    image: str
    category: str
    price: float | int = Field(gt=0)
    currency: Literal["SAR"]
    dietary: Dietary
    spiceLevel: int = Field(ge=0, le=3)

    @model_validator(mode="after")
    def consistent(self):
        if self.dietary.vegan is True and self.dietary.vegetarian is not True:
            raise ValueError("Vegan must imply confirmed vegetarian")
        if not self.image.startswith("https://cdn.dummyjson.com/recipe-images/"):
            raise ValueError("Unexpected image origin")
        return self


def terms(value: str) -> str:
    # Deliberately small matching rule; not a complete ingredient ontology.
    words = re.findall(r"[^\W_]+", normalize(value))
    return " ".join(word.rstrip("s") for word in words)


def contains(needle: str, haystack: str) -> bool:
    return f" {terms(needle)} " in f" {terms(haystack)} "


class Menu:
    def __init__(self, path: Path):
        raw = json.loads(path.read_text())
        self.items = [MenuItem.model_validate(i) for i in raw["recipes"]]
        self.by_id = {i.id: i for i in self.items}
        if not self.items or len(self.by_id) != len(self.items):
            raise ValueError("Empty menu or duplicate IDs")

    @staticmethod
    def eligible(item: MenuItem, c: Constraints) -> bool:
        if c.unsupported:
            return False
        if c.category and terms(c.category) != terms(item.category):
            return False
        if c.cuisine and normalize(c.cuisine) != normalize(item.cuisine):
            return False
        if c.max_price is not None and item.price > c.max_price:
            return False
        if c.max_spice is not None and item.spiceLevel > c.max_spice:
            return False
        if c.vegetarian is True and item.dietary.vegetarian is not True:
            return False
        if c.vegan is True and item.dietary.vegan is not True:
            return False
        if any(contains(x, item.name) for x in c.excluded_dishes):
            return False
        if any(
            contains(x, ingredient)
            for x in [*c.excluded_ingredients, *c.allergens]
            for ingredient in item.ingredients
        ):
            return False
        return not any(
            not any(contains(x, i) for i in item.ingredients) for x in c.required_ingredients
        )

    @staticmethod
    def score(item: MenuItem, profile: list[dict]) -> int:
        score = 0
        for p in profile:
            dim, subject, value = p["dimension"], p["subject"], p["value"]
            match = (
                (dim == "cuisine" and normalize(item.cuisine) == subject)
                or (dim == "ingredient" and any(contains(subject, x) for x in item.ingredients))
                or (dim == "dish" and contains(subject, item.name))
            )
            if match:
                score += 3 if value == "like" else -6
            if dim == "spice":
                score += 2 if item.spiceLevel <= int(value) else -3
        return score

    def search(
        self,
        active: Constraints,
        filters: SearchFilters | None = None,
        profile: list[dict] | None = None,
    ) -> list[MenuItem]:
        f = filters or SearchFilters()
        eligible = [i for i in self.items if self.eligible(i, active) and self.eligible(i, f)]
        if f.query:
            eligible = [
                i
                for i in eligible
                if contains(f.query, " ".join([i.name, i.cuisine, *i.ingredients]))
            ]
        if f.sort_by == "price_desc":
            eligible.sort(key=lambda i: (-i.price, i.id))
        elif f.sort_by == "price_asc":
            eligible.sort(key=lambda i: (i.price, i.id))
        else:
            eligible.sort(key=lambda i: (-self.score(i, profile or []), i.price, i.id))
        return eligible[: f.limit]

    def get(self, ids: list[int], active: Constraints) -> list[MenuItem]:
        return [
            self.by_id[i] for i in ids if i in self.by_id and self.eligible(self.by_id[i], active)
        ]

    def validate_selection(self, ids: list[int], active: Constraints, seen: set[int]):
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate selections")
        for item_id in ids:
            if item_id not in seen or item_id not in self.by_id:
                raise ValueError("Selected ID was not retrieved from the menu tools")
            if not self.eligible(self.by_id[item_id], active):
                raise ValueError("Selected item violates an active requirement")
