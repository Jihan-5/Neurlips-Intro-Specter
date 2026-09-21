# E4 exploratory operational definition (fixed before computing the rate)

Source: the public PersonalWAB `user_profiles.json` and three
`user_history_part_*.json` files; source hashes are recorded with the output.
All users are included in the denominator, and absent evidence is reported.

A **brand-preference/history discordance** is a preferred brand named explicitly
in the user's `Brand Preference` field for which at least two distinct historical
products have ratings, and every observed rating is at most two stars. Match
brand names by case-folded alphanumeric exact equality against product `Brand`
(or `store` only when Brand is absent). Use only interactions marked `history`,
not test targets. Do not infer preference from demographic attributes.

Report the fraction of all users with at least one such discordance, coverage,
and the number of matched brands/reviews. This conservative rule detects one
operational type of inconsistency; it is not a prevalence estimate for all
semantic contradictions. Preferences are soft, products can disappoint within a
preferred brand, and there are no timestamped profile versions. No LLM judge or
synthetic corruption is introduced. Label this analysis exploratory and do not
promote its fraction to an unqualified “organic contradiction rate.”
