# Menu schema and limitations

`menu.json` is a JSON object with `metadata` and `recipes`. Despite the wrapper name,
each of its **50** entries is one fictional menu item. IDs 1–50, ordering, names,
ingredients, cuisine and image URLs are retained from the recipe source.

| Field | Meaning |
| --- | --- |
| `id` | Stable integer source ID; do not regenerate |
| `name` | Exact source display name |
| `ingredients` | Exact array of source strings, including preparation qualifiers |
| `cuisine` | Source cuisine label |
| `image` | Original HTTPS DummyJSON recipe image URL |
| `category` | Editorial Starters, Salads, Mains, Desserts or Beverages |
| `price` | Fictional positive SAR amount per individual menu item/order |
| `currency` | `SAR` |
| `dietary.vegetarian`, `dietary.vegan` | Demo ingredient-based boolean or `null` (unresolved) |
| `spiceLevel` | Fictional fixed preparation: 0 none, 1 mild, 2 medium, 3 hot |
| `allergens` | Conservative inferred labels, including compound-ingredient assumptions |
| `allergenStatus` | Source metadata only; ignored by filtering and display |

Metadata identifies source filename/hash, fictional pricing basis, spice scale,
annotation notes, and the allergen caveat. Startup validates the complete records,
positive prices, spice bounds, currency, duplicate IDs, image origin, and vegan ⇒
vegetarian consistency. It loads the menu once into the application service.
Filtering scans this in-memory list; no embeddings/index/server are needed.

Borscht’s vegetarian classification is unknown because the source permits beef or
vegetable broth. Vegan classifications contain editorial component assumptions.
An empty allergen list means no labels were inferred, rather than verified absence.
Cross-contact and full compound ingredient specifications are unknown. The application uses the `allergens` labels directly to exclude matching dishes,
as requested for this demo; `allergenStatus` does not block recommendations.
Exclusions use simple case-insensitive word/phrase matching with plural normalization;
this is not a complete synonym/ingredient ontology and cannot establish medical safety.

Prices are per item, not a recipe batch or entire multi-item order. Portions,
servings, calories, substitutions, availability, certification and preparation changes
are unavailable. Alcohol-containing ingredients are preserved; no halal inference is
permitted. See the original [MENU_DATA_NOTES.md](../MENU_DATA_NOTES.md) for the full
assumptions, source limitations and regeneration procedure. The build never rewrites
the menu or original recipe files.
