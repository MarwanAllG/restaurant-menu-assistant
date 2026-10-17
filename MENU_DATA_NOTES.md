# Demo menu data

This repository ships a prepared 50-item `menu.json` derived from DummyJSON recipe
data. It preserves source IDs, names, ingredient arrays, cuisines and image URLs.
The `recipes` wrapper is retained for compatibility with the source structure.
Raw recipe backups, preparation scripts and notebooks are local development material
and are not required to run or deploy this app.

Added fields are editorial demo annotations, not facts supplied by DummyJSON:

- `category`: Starters, Salads, Mains, Desserts, or Beverages. Some dishes could fit
  multiple categories; one primary menu category is assigned to each.
- `price` and `currency`: fictional SAR prices per menu order, not recipe batches.
  Portions are not specified by the source; do not use the removed batch servings
  to calculate a menu price or claim a portion size.
- `dietary.vegetarian` and `dietary.vegan`: ingredient-based demo classifications.
  `null` means unresolved, not false. Borscht is unresolved for vegetarian suitability
  because its source explicitly permits beef or vegetable broth. Cheese is assumed
  to use vegetarian rennet; plant-based bread, wraps, falafel, and vegetable broth
  are assumed for vegan classifications. Alcohol-containing items are preserved;
  no halal certification or alcohol-free claim is made.
- `allergens`: conservative inferred labels, including assumptions about compound
  ingredients. `allergenStatus` is `inferred_unverified` for every item. Empty arrays
  mean no listed/inferred allergens, NOT verified absence. Cross-contact is unknown.
  Do not let the assistant guarantee suitability for an allergy from this dataset.
- `spiceLevel`: fictional fixed preparation, 0 none, 1 mild, 2 medium, 3 hot. These
  are chosen values because source recipes omit quantities. Level 1 on cucumber
  avocado rolls includes the listed wasabi accompaniment. Changes or omissions are
  not supported unless explicitly added to the menu later.

Compound-ingredient assumptions behind allergen annotations: ordinary wheat-based
soy/teriyaki sauces, egg-based fresh fettuccine/linguine and the noodle option in
shrimp-asparagus stir-fry, wheat ramen, oyster-containing oyster sauce, shrimp-based
Thai curry pastes, wheat/soy peanut dipping sauce, celery-containing vegetable
broth, mustard-containing mayonnaise and wasabi, pine-nut pesto, milk/soy chocolate
components, and sulphites in wine/balsamic glaze. Tree nuts in the blueberry smoothie
refer to almonds; tree nuts in pesto refer to pine nuts (a demo taxonomy convention,
not a claim about regulatory classifications). These assumptions require component
specifications before they can become verified restaurant declarations.

The ingredient arrays remain exact source copies. They are not complete restaurant
recipe specifications: some cooking instructions mention ingredients absent from
the arrays, mixtures are not expanded, and wooden skewers appear as an ingredient.
Unknown component details must not be invented by the recommendation agent.

Removed fields: `instructions`, `prepTimeMinutes`, `cookTimeMinutes`, `servings`,
`difficulty`, `caloriesPerServing`, `tags`, `userId`, `rating`, `reviewCount`, and
`mealType`. Calories are removed because a restaurant portion is not defined; menu
categories replace meal types, and cuisine plus ingredients retain useful preference
information without the inconsistent source tags.

The application treats the prepared menu as read-only. It validates record structure,
positive prices, spice bounds and dietary consistency when loading the menu.
