import json
import os
import ast

# Evaluation Runner for writing-hyper-api-code skill
# Aligned with 001_prompt_evals_fns.ipynb logic

EVALS_FILE = "../evals/evals.json"

GRADER_TEMPLATE = """
### Grader Prompt Template (JSON Format)
---
System: You are an expert Tableau Hyper API code reviewer.

Task: Evaluate the following AI-generated solution.

Output Format:
Provide your evaluation as a structured JSON object:
- "strengths": An array of 1-3 key strengths.
- "weaknesses": An array of 1-3 key areas for improvement.
- "reasoning": A concise explanation.
- "score": A number between 1-10.

Prompt: {prompt}
Expected Criteria: {expected_output}
Solution to Evaluate:
{generated_code}
---
"""

def validate_python_syntax(code):
    try:
        ast.parse(code)
        return 10
    except SyntaxError:
        return 0

def load_evals():
    with open(EVALS_FILE, 'r') as f:
        return json.load(f)

def main():
    print("--- Hyper API Skill Evaluation Runner (Notebook Aligned) ---")
    try:
        data = load_evals()
        evals = data.get('evals', [])
        
        print(f"Loaded {len(evals)} evaluation cases.\n")
        
        for item in evals:
            print(f"ID {item['id']}: {item['prompt'][:60]}...")
            print("-" * 30)
            
        print("\nTo run an evaluation:")
        print("1. Select an ID from above.")
        print("2. Copy the JSON Grader Prompt Template below.")
        print("3. Submit to an LLM to get the 'Model Score'.")
        print("4. Use the `validate_python_syntax()` function in this script for the 'Syntax Score'.")
        print("5. Aggregated Score = (Model Score + Syntax Score) / 2")
        
        print("\n" + GRADER_TEMPLATE.format(
            prompt="{{eval.prompt}}", 
            expected_output="{{eval.expected_output}}", 
            generated_code="[PASTE_CODE_HERE]"
        ))
        
    except FileNotFoundError:
        print(f"Error: Could not find {EVALS_FILE}")

if __name__ == "__main__":
    main()
