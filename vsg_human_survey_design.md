# VSG Human Survey — Item Design v2 (4 items per image)

Source: `vsgv2_full_finalized.jsonl` (549 rows, 13 relations, 3 `leak_attributes` with probes on every row). Filled item text: `vsg_survey_items.csv` (13 prompts × 4 items = 52 rows).

## 1. Layout
- 13 prompts × 2 conditions (base, Gemma4-augmented) = 26 images, one T2I model.
- Raters see only the original prompt ("A that looks like B"). Condition is hidden.
- 4 items × 26 images = 104 responses, about 10–12 min.

## 2. Items (1–5; 1 = strongly disagree, 5 = strongly agree)

| # | Template | Maps to |
|---|---|---|
| Q1 | This image is a good visual simile of the prompt. | Human criterion |
| Q2 | The main object in this image is {A}, and {B} does not appear as a separate object anywhere in the image. | CS_anchor as a whole (subject salience + no juxtaposition) |
| Q3 | {A} has the {licensed-channel phrase} of {B}. | CS_resem · relation-conditioned s_attr |
| Q4 | At least one of these appears on or around {A}: {leak 1}; {leak 2}; {leak 3}. | Leak / over-rendering (max over 3 probes) |

- The Q3 phrase comes from `template_prompt` (e.g., "outline", "surface texture").
- Q4 wording matches a **max** aggregation of the three judge probe scores. If the metric uses mean instead, rewrite Q4 or split it into 3 items.

## 3. Sub-scores with no human counterpart (state in paper)
| Dropped | What goes unvalidated | Partial cover |
|---|---|---|
| s_obj item | CS_resem margin penalty max(0, s_obj − s_subj); human complementarity check | Q2 low (wrong-anchor), Q4 (leak) |

## 4. Prompts (one per relation)
12 pilot20 relation-coverage prompts + **rare0041 "a rusted iron gate that looks like a pumpkin"** (`patina_weathering`). None of the 5 `_warnings` rows are used.

## 5. Order and bias controls
1. Q1 alone on screen first, then Q2–Q4.
2. Never show a prompt's two images back-to-back; 2 counterbalanced forms.
3. Shuffle leak attribute order within Q4.
4. 2 attention checks. Log Prolific PID, form, item order, response time.

## 6. Analyses
- Q2 is compared against the full CS_anchor column, not the subject score alone. Q2 bundles two claims, so a low rating cannot say which one failed.
- Proxy ↔ criterion: judge sub-score vs. matching human item (Spearman), pooled over 26 images, per judge lineage.
- Augmentation preference: Q1(aug) − Q1(base) per prompt.
- Krippendorff's α (ordinal) per item; expect Q4 lowest.

## 7. Limits
- 26 images, 1 prompt per relation: pooled claims only, no per-relation claims.
- One T2I model: no cross-model claims.
- Absolute ratings, not pairwise; preference derived from Q1.
