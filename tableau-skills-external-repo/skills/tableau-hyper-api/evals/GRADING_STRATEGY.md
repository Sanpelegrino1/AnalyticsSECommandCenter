# Grading Strategy: Model-as-a-Judge

To ensure high-quality, enterprise-grade Hyper API code, we use a tiered grading approach.

## 1. The Reasoning Requirement (Strengths & Weaknesses)
When using an LLM to grade generated code, **never ask for a score immediately**. 

Models tend to "center" their scores (often defaulting to a 6/10) if they don't deliberate first. Always ask the model to list **Strengths** and **Weaknesses** before assigning a final grade.

## 2. Structured JSON Output
To automate scoring, the Model Grader should respond with a structured JSON object. This allows you to aggregate the "Model Score" with the "Syntax Score" (calculated via `ast.parse`).

## 3. Grader Prompt Template
Use the following prompt when asking an LLM to evaluate the skill (Aligned with `001_prompt_evals_fns.ipynb`):

```markdown
System: You are an expert Tableau Hyper API code reviewer.

Task: Evaluate the following AI-generated solution.

Output Format:
Provide your evaluation as a structured JSON object with the following fields:
- "strengths": An array of 1-3 key strengths.
- "weaknesses": An array of 1-3 key areas for improvement.
- "reasoning": A concise explanation.
- "score": A number between 1-10.

Prompt: {{eval.prompt}}
Expected Criteria: {{eval.expected_output}}
Solution to Evaluate:
{{model_output}}
```
