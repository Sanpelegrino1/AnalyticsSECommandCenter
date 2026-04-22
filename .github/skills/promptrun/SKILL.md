---
name: promptrun
description: "Strengthen rough instructions into a sharper, higher-leverage prompt and then execute it immediately. Refine loose requests, preserve intent, ask only essential follow-up questions, briefly show the improved prompt, and continue with it as the working brief."
argument-hint: "Paste rough instructions plus any known goal, target, context, constraints, or output expectations."
user-invocable: true
disable-model-invocation: false
model: "GPT-5 (copilot)"
---

# Promptrun

Use this skill when the user wants a rough prompt improved and then acted on without a separate approval step.

## Core goal

- Convert loose, underspecified, or awkward instructions into a stronger prompt.
- Preserve the user's intent.
- Add clarity, structure, constraints, and success criteria only where useful.
- Use the refined prompt as the working brief and proceed without waiting for a separate confirmation.

## Default behavior

1. Inspect the user's raw instructions.
2. Ask only about missing information that materially changes the result.
3. Rewrite the input into a stronger prompt.
4. Briefly show or summarize the improved prompt.
5. Immediately use the strengthened prompt as the working brief and continue execution.

## Execution rules

- Do not stop after producing the strengthened prompt.
- Do not ask whether to run it now unless there is a genuine blocker or ambiguity.
- If the prompt can be executed safely with available information, proceed.
- If the input is too incomplete to execute truthfully, ask the minimum clarifying questions needed and then continue.

## Intake pattern

Extract or infer only what is needed from the raw request:

- Goal
- Target
- Context
- Constraints
- Output
- Quality bar

If the input is empty, too vague, or too short to improve responsibly, ask the user to classify the prompt type first:

- `Code or implementation prompt`
- `Writing prompt`
- `Research or analysis prompt`
- `Agent instruction or system prompt`
- `Other`

Then ask only 1-4 meaningful follow-up questions when needed.

## Follow-up question policy

- Ask questions only when the answer would materially change the prompt or make execution unsafe or untruthful.
- Prefer a small number of high-leverage questions over a long intake.
- If the likely defaults are obvious and low-risk, proceed without asking.
- Never ask questions just to make the prompt look more formal.

## Prompt construction standard

Produce a refined prompt that is compact, specific, and easy to execute. Use this preferred output shape unless the prompt type clearly needs a different structure:

- Goal
- Context
- Requirements
- Do Not
- Output
- Success Criteria

Add only the constraints and success criteria that improve the result. Do not bloat the prompt.

## Adaptation modes

### Agent instruction or system prompt

- Emphasize operating rules, priorities, escalation boundaries, and decision criteria.
- Make execution boundaries explicit.
- Remove ambiguity around when to ask questions versus act.

### Coding prompt

- Clarify the target code surface, desired behavior, constraints, validation path, and expected deliverable.
- Preserve repo or environment constraints if the user supplied them.

### Writing prompt

- Clarify audience, tone, structure, key points, exclusions, and completion criteria.

### Research or analysis prompt

- Clarify the question, scope, evidence standard, comparison criteria, and preferred output format.

## Output behavior

Return:

1. A short note on any assumptions or gaps that mattered.
2. The strengthened prompt itself or a brief summary of it.
3. Immediate continuation using that refined prompt as the working brief.

## Guardrails

- Do not erase the user's intent.
- Do not pad with generic fluff.
- Do not invent unnecessary requirements.
- Do not add speculative constraints unless they clearly reduce ambiguity.
- Do not pause for a separate approval step once the prompt is strong enough to execute.

## Success criteria

- The refined prompt is clearer and more actionable than the original.
- The user's intent is preserved.
- Questioning stays minimal and high-signal.
- The improved prompt is shown or summarized briefly.
- Execution proceeds automatically once the prompt is strong enough.