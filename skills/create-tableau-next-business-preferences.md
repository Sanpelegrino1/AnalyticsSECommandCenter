# Create Tableau Next Business Preferences

## Purpose

Create concise, domain-specific Tableau Next business preferences for a semantic model so Analytics Q&A is more likely to answer directly and less likely to ask clarifying questions.

## When to use it

Use this after a semantic model already exists and the remaining task is to improve Analytics Q&A behavior with jargon, interpretation defaults, and output guidance that belongs in business preferences rather than calculated fields or descriptions.

## Inputs

- Semantic model name or target context.
- Model schema context, ideally from a manifest, semantic-model spec, or live semantic-model definition.
- Business vocabulary, default metrics, default sort behavior, and any preferred fallback interpretations.
- Optional limit on instruction count or instruction style.

## Prerequisites

- The semantic model already exists or its schema is known well enough to write grounded preferences.
- The author knows the business language well enough to define non-conflicting defaults.
- Current repo status: there is no verified repo-native API path yet for writing business preferences directly to a Tableau Next semantic model.

## Exact steps

1. Read the semantic-model inputs first: prefer the manifest, semantic-model spec, or live semantic-model definition over guessing from memory.
2. Identify only the missing business context that is not better handled by calculated fields, descriptions, permissions, or role-specific models.
3. Write short, explicit instructions, one per line, each starting with `#`.
4. Favor interpretation defaults that help the agent answer broad questions directly, such as the default metric for "top", "largest", "pipeline", "best performing", "at risk", or "new".
5. Keep each instruction concise and specific to the model's real fields, terminology, or joins.
6. Avoid conflicting preferences, feature-control requests, visual-format requests, or instructions that require unsupported calculations.
7. If a direct API write path is later verified in this repo, use it and report what was written.
8. Until that path exists, return the preferences as a paste-ready block in chat for manual entry into the semantic model.

## Validation

- Every instruction starts on a new line with `#`.
- The preferences refer to real model concepts, fields, or business vocabulary.
- The list increases answerability without forcing unnecessary clarifications.
- The list avoids calculated-field logic, blocking rules, and response-formatting directives that Tableau Next does not support through business preferences.

## Failure modes

- Preferences are too vague and simply restate business background instead of actionable interpretation guidance.
- Preferences conflict with each other, for example defaulting "top reps" to quota attainment in one line and ACV in another.
- Preferences try to perform formulas, force visual output, or disable topics, which business preferences do not support.
- The model context is too thin to ground the preferences safely; in that case, read the manifest or semantic-model spec first.
- An attempted direct API update should be treated as unsupported unless a verified endpoint and payload field are added to this repo.

## Cleanup or rollback

- Remove or rewrite any preference that repeatedly causes wrong defaults or conflicts with later model changes.
- Keep the list short enough to stay maintainable; prefer replacing weak lines over endlessly appending new ones.

## Commands and links

- `scripts/tableau/upsert-next-semantic-model.ps1`
- `scripts/tableau/inspect-next-semantic-model.ps1`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `tmp/*.semantic-model.spec.json`
- https://help.salesforce.com/s/articleView?id=data.c360_a_sl_biz_preferences_bestp.htm&type=5