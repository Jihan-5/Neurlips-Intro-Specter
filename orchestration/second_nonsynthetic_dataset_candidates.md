# Candidate real (non-synthetic) datasets for a second multi-fault-injection benchmark

Context: `intro_specter/benchmarks/travelplanner_real.py` loads `osunlp/TravelPlanner`
(HF `datasets`, validation split, 180 real examples) and treats its native fields
(budget, days, destination, local cuisine/house-rule/transportation constraints) as
real, independently-violable constraints on top of which an LLM agent must "produce a
concrete day-by-day plan." This file ranks real, publicly-downloadable candidates for a
SECOND dataset of the same character. Research method: web search + direct verification
of each HF dataset's `datasets-server` schema/size/license/gating via the HF Hub API
(`huggingface.co/api/datasets/<id>` and `datasets-server.huggingface.co/info|size`),
not guessed from memory. All dataset IDs below were confirmed to exist and to expose
the listed columns as of 2026-07-26.

---

## #1 (RECOMMENDED FIRST BUILD) — `AkashPS11/recipes_data_food.com`

- **Source**: Food.com recipes (the well-known "Food.com Recipes and Reviews" corpus,
  mirrored to HF as a plain CSV/Parquet dataset). Verified via
  `datasets-server.huggingface.co/info?dataset=AkashPS11%2Frecipes_data_food.com` and
  `huggingface.co/api/datasets/AkashPS11/recipes_data_food.com`.
- **Size**: 1,048,543 rows, 29 columns, ~187MB in memory / ~34MB raw CSV — trivially
  downloadable, no special handling needed. (We'd sample a few hundred rows the same
  way `travelplanner_real.py` samples 60 of 180 via a seeded RNG index, so the large
  corpus size is a non-issue — if anything it gives more headroom than TravelPlanner's
  180-row pool.)
- **License / access**: `license:mit` tag on the HF repo, **not gated** (`"gated": false`
  confirmed via the Hub API). No sign-in, no agreement, no `trust_remote_code` needed —
  strictly more open than TravelPlanner itself.
- **Real native constraint fields** (confirmed column names from the dataset schema):
  `CookTime`, `PrepTime`, `TotalTime` (ISO-8601 duration strings — real prep-time
  constraint), `RecipeCategory` and `Keywords` (free-text but recipe-site-authored tags,
  e.g. cuisine/diet-adjacent labels), `RecipeIngredientParts` /
  `RecipeIngredientQuantities` (real ingredient list — supports "must/must-not contain
  ingredient X" constraints), `RecipeServings` / `RecipeYield` (real serving-size
  constraint), and a full real nutrition panel (`Calories`, `FatContent`,
  `SaturatedFatContent`, `SodiumContent`, `CarbohydrateContent`, `SugarContent`,
  `ProteinContent`, `FiberContent` — supports "must respect a calorie/macro budget"
  constraint, directly analogous to TravelPlanner's dollar budget). `AggregatedRating` /
  `ReviewCount` are available as optional secondary signal.
- **Natural NL generation task on top**: "Given a diner with these constraints (prep
  time ≤ X minutes, must be vegetarian/gluten-free per stated dietary need, calorie
  budget ≤ Y, must serve Z people, must not use ingredient W), suggest a recipe and
  write it out (ingredients + instructions)." This is a direct structural analogue of
  TravelPlanner's "produce a day-by-day plan within budget" — same shape (multiple
  independent hard constraints → one generated free-text artifact to verify against
  each).
- **Adaptation effort: LOW.** Every constraint is already a clean structured column
  (numeric or short string), not something that has to be mined out of a paragraph of
  free text — this is easier to build against than TravelPlanner itself, whose
  `local_constraint` field required custom dict-literal parsing
  (`travelplanner_real.py`'s `_parse_local`). The `rule()` function is a set of direct
  substring/numeric checks (time string parse, ingredient-absence substring check,
  calorie-sum sanity check, servings-mention check) — same style as
  `_make_rule()` in `travelplanner_real.py`.
- **Domain diversity bonus**: recipes are a genuinely different domain from
  TravelPlanner's trip-planning, which strengthens a generalization argument
  ("holds across both a travel-planning and a recipe-recommendation domain") rather
  than reusing a travel/booking-adjacent domain.

---

## #2 — `McAuley-Lab/Amazon-Reviews-2023` (per-category `raw_meta_*` configs)

- **Source**: the official, widely-cited UCSD McAuley Lab Amazon Reviews 2023 release
  (real Amazon product catalog + reviews, collected through Sept 2023). Verified via
  the dataset's own site (`amazon-reviews-2023.github.io`) and the HF Hub API
  (`"gated": false`).
- **Size**: organized as 33 real product categories, each its own loadable config
  (e.g. `raw_meta_All_Beauty`, `raw_meta_Subscription_Boxes`). Smallest categories are
  genuinely small and manageable (e.g. Subscription_Boxes ≈ 641 items, Gift_Cards ≈
  1.1K items) — lets us pick a category sized comparably to TravelPlanner's 180 rows
  rather than confronting the full 571M-review corpus.
- **License / access**: not gated, no sign-in required. Caveat: the HF repo carries no
  explicit `license:` tag (unlike TravelPlanner/Food.com), and loading requires
  `trust_remote_code=True` (the repo ships a custom loading script) plus specifying the
  exact `raw_meta_<Category>` config string — mild extra friction versus a plain
  Parquet dataset, but this is a standard, long-established academic dataset with no
  commercial restriction stated.
- **Real native constraint fields** (confirmed from the dataset's own documentation
  page): `price` (real USD listing price — note many items show `price: None` and would
  need a filter step), `store` (real brand/seller name), `categories` (real hierarchical
  category path), `features` (real bullet-point spec list — supports "must have
  feature/spec X"), `average_rating` / `rating_number`, `details` (materials, brand,
  sizes).
- **Natural NL generation task on top**: "Given a shopper with these constraints (budget
  ≤ $X, must be brand Y or a specific material, must have feature Z), recommend a
  product and write the recommendation." Direct product-recommendation analogue of
  TravelPlanner's plan-writing task.
- **Adaptation effort: MEDIUM.** Structured fields exist, but `price` needs a
  None-filtering/sampling step to guarantee usable examples, and `features`/`details`
  are semi-structured lists needing light parsing (comparable to `_parse_local` in
  `travelplanner_real.py`, so not a new category of difficulty — just one extra
  filtering pass beyond what Food.com needs).
- **Why ranked below Food.com**: extra loading friction (`trust_remote_code`,
  category-choice step, price-None filtering) and no explicit license tag, versus
  Food.com's plain MIT-licensed CSV with clean numeric columns.

---

## #3 — `kraina/airbnb`

- **Source**: real Airbnb listings from 10 European cities, originally published as
  supplementary data for a peer-reviewed tourism-economics paper (Gyódi & Nawaro 2021,
  *Tourism Management*, DOI 10.1016/j.tourman.2021.104319), mirrored from Zenodo
  (10.5281/zenodo.4446043) to HF. Verified via `datasets-server.huggingface.co/info`.
- **Size**: 51,700 listings total (weekday/weekend subsets ~25.5K/~26.2K each) — ample
  headroom to sample a few hundred.
- **License / access**: `license:cc-by-4.0` confirmed on the HF repo, **not gated**.
  Fully open, attribution-only.
- **Real native constraint fields**: `city` (real location), `realSum` (real nightly
  price), `room_type` + `room_shared`/`room_private` (real booking-type constraint),
  `person_capacity` and `bedrooms` (real capacity constraint), `host_is_superhost`
  (real host-quality constraint), `cleanliness_rating` / `guest_satisfaction_overall`
  (real quality-threshold constraint), `dist`/`metro_dist` (real proximity constraint).
- **Natural NL generation task on top**: "Given a guest with these constraints (budget
  ≤ realSum, needs a private room, capacity ≥ N guests, must be within metro_dist of
  transit), write the booking confirmation / recommend the listing."
- **Adaptation effort: LOW–MEDIUM.** All fields are clean numeric/boolean/string columns
  — easy extraction — but the *task framing* ("write a booking confirmation") is closer
  in flavor to TravelPlanner's own domain (travel/accommodation) than Food.com's recipe
  domain, which weakens the domain-diversity argument for a generalization claim even
  though the mechanics are equally easy to build.

---

## #4 — `datahiveai/recipes-with-nutrition` (backup only, same domain as #1)

- **Size**: 39,447 recipes, CSV, ~450MB. Verified via WebFetch of the HF dataset card.
- **Real fields**: `diet_labels`, `health_labels`, `cautions`, `cuisine_type`,
  `meal_type`, `dish_type`, `servings`, `calories`, structured `ingredients`
  (quantity/measure/food/weight), full `total_nutrients` panel. No explicit prep-time
  field (a gap versus Food.com).
- **License caveat**: **CC BY-NC 4.0 — non-commercial only.** This is a meaningfully
  worse licensing position than TravelPlanner or Food.com for a paper artifact meant to
  be freely redistributable; flagged as the main reason to prefer #1 over this one.
- **Verdict**: redundant with #1 (same recipe domain, smaller, more restrictive
  license, fewer usable constraint types). Only worth using if Food.com's schema turns
  out to have a blocking data-quality problem on inspection.

---

## Considered and rejected

- **`mbien/recipe_nlg`** (RecipeNLG, >1M recipes): requires a **signed non-commercial
  research license** from Poznań University of Technology, with an indemnification
  clause — meaningfully more restrictive than TravelPlanner's openness, and its columns
  (`title`, `ingredients`, `directions`, `ner`) lack structured dietary/time/serving
  fields, so most "constraints" would have to be mined from free text. Rejected: worse
  licensing AND worse structure than Food.com.
- **E-commerce scraped datasets** (`crawlfeeds/tesco-grocery-uk`,
  `UniqueData/asos-e-commerce-dataset`, `thebeautyapi/beautyproducts`): real listings,
  but these are commercial data-vendor scrapes republished on HF without clear
  provenance/licensing statements — riskier to cite as a benchmark artifact than the
  academically-published Amazon-Reviews-2023 or the MIT-licensed Food.com mirror.
  Not pursued further given #1/#2 already satisfy the requirements with cleaner
  provenance.
- **Job-postings datasets** (`azrai99/job-dataset`, `yiqing111/Engineering_Jobs_Insight_Dataset`):
  real salary/location/skill fields exist, but the natural "task on top" (write a job
  description / cover letter) is a weaker match to an *agent-response-verification*
  framing than recommend-a-recipe/product/booking, and provenance/licensing of the
  underlying scrapes is unclear. Deprioritized rather than fully verified in depth,
  given three stronger candidates were already confirmed.

---

## Recommendation

**Build `food_com_real.py` first**, against `AkashPS11/recipes_data_food.com`.

Reasoning: it beats every other candidate on the two things that matter most for
matching TravelPlanner's bar —
1. **Openness**: MIT-licensed, not gated, no `trust_remote_code`, no signed agreement —
   strictly easier to justify in a paper than TravelPlanner's own license, and clearly
   easier than RecipeNLG, `recipes-with-nutrition` (CC-BY-NC), or Amazon-Reviews-2023
   (no license tag, requires `trust_remote_code`).
2. **Structure**: every candidate constraint (prep time, dietary/category tags,
   ingredient list, servings, full nutrition panel) is already a clean typed column —
   the lowest-adaptation-effort option of the group, arguably lower-effort than
   TravelPlanner's own `local_constraint` field, which needed custom parsing.

It also adds genuine domain diversity (recipes vs. travel-planning), which is the more
persuasive generalization story for a rebuttal than a second travel/booking-flavored
dataset (`kraina/airbnb`, ranked #3 partly for that reason).

**If reviewers specifically want e-commerce/product-recommendation diversity** rather
than a second food-adjacent dataset, `McAuley-Lab/Amazon-Reviews-2023` (a small
category config, e.g. `raw_meta_Subscription_Boxes` or `raw_meta_All_Beauty`, sampled
down to match TravelPlanner's scale) is the solid second choice — real price/brand/
category/feature constraints, well-known and citable dataset, just slightly more
loading friction (`trust_remote_code=True`, category selection, price-None filtering)
than Food.com.

No loader code has been written — this file is research/recommendation only, per the
task scope.
