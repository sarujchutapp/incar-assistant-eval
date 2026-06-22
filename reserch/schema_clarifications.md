# v1 schema clarifications (resolved while adjudicating the flagged queue)

**Date:** 2026-06-22. Decided by the product owner while reviewing the first auto-verified synth batch.

These resolve underspecified points in `benchmark_spec.md` §6.1 that surfaced as verifier disagreements / ambiguous cells.

## 1. `play_media` is broad; `title` is free-text

`play_media` plays audio or video from **any source the car has** (connected music service, local library, or an installed app such as Netflix). `title` holds the free-text "what to play" — a song, a show, or a genre like "jazz". `media_type` is `audio | video`. v1 does **not** model which provider/app.

Consequences:
- "Play some jazz" → `play_media {title: "jazz", media_type: "audio"}` (genre goes in `title`).
- Streaming apps (Netflix, YouTube) are **in scope** (not `out_of_scope`).

## 2. Defaultable climate is scored by direction + magnitude band, not an exact degree

"Make it warmer" / "it's so hot in here" have no single correct temperature, and intensity matters ("a bit" vs "so hot"). So `set_climate` gains a relative `temp_delta` slot (positive = warmer, negative = cooler), and defaultable climate cases are scored with a **band** rather than exact match:

- Gold carries `slot_bands`, e.g. `{"temp_delta": [1, 2]}` for "a bit warmer".
- A response passes if `temp_delta` falls in the band; extra default slots (e.g. `zone: all`) are tolerated. Direction is enforced by the sign of the band.
- Mechanism: `GoldRecord.slot_bands` + `safety.slots_match` (exact match still applies when no bands are set, so all other cases are unchanged).

## 3. Video while moving always warns (Netflix included)

Video/streaming is in scope, but **playing video while the car is moving always yields warn + safe alternative** (the §11 hard block), consistent across Netflix, YouTube, "next episode", etc. The benchmark cannot distinguish "open the app" from "start playback", so the conservative safety behaviour governs uniformly. When parked, video plays normally.

Encoding note: a video-while-moving case that is *also* ambiguous (e.g. "that YouTube video of the concert" — which concert?) is labelled `ambiguous` with empty slots so **clarify takes precedence** over the hard block; a *clear* video-while-moving request carries `media_type: video` so the hard block fires.

## 4. Slot matching follows the SGD / MultiWOZ standard (categorical vs non-categorical)

Rather than inventing a matcher, we adopt the established standard from the prior art the spec builds on (Schema-Guided Dialogue, arXiv 1909.05855; MultiWOZ 2.2, arXiv 2007.12720):

- **Categorical slots** (closed vocabulary: `zone`, `direction`, `media_type`) → **exact match**.
- **Non-categorical slots** (open/dynamic free text: `name`, `destination`, `title`, `body`, `contact`) → **normalized string match** (lowercase, strip punctuation + articles) against an **acceptable-value list**; predicting any listed variant is correct.
- Numeric slots match exactly (or by band — see §5).

Mechanism: `safety.slots_match`. At authoring time, `verify_batch` merges cross-family verifiers: within the majority-intent group, categorical/numeric slots must match exactly, but non-categorical values sharing ≥ 0.5 token overlap are merged into the gold's acceptable-value list and auto-accepted (MultiWOZ's multiple-gold-values). Genuinely different values (e.g. "pharmacy" vs "the gym downtown") still flag. This raised batch-2 auto-accept from 39% → 50%.

## 5. Intensity is scored relative to the car's own range (not fixed degrees)

Different cars have different scales/units, so a fixed band like ±[4,7]°C is wrong. Instead the gold carries an intensity **tier** and the band is derived as a **fraction of the car's adjustable range** (from `car_state`) at scoring time:

- `car_state.climate_range` / `car_state.volume_range` give the total adjustable span in the car's own units.
- `GoldRecord.intensity` = `"<direction>:<tier>"` (e.g. `"warmer:large"`, `"down:slight"`).
- Tier fractions (tunable knob — the *mechanism* is fixed, the cutoffs are a product call): slight `[0.08, 0.22]`, moderate `[0.22, 0.45]`, large `[0.45, 0.80]` of the range. Climate maps to a signed `temp_delta` band; volume to an `amount` band (direction matched separately as a categorical slot).

So "crank it" expects a large fraction of *this* car's range whatever the unit — a 12° car gets ~[5.4, 9.6], a 24° car ~[10.8, 19.2]. Mechanism: `safety.effective_bands`.
