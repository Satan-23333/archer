#!/usr/bin/env python3
import os
import sys
import json
import argparse
from openai import OpenAI
def get_system_prompt():
    """
    Returns the System Prompt for the LLM.
    """
    return """You are the Specification Interpreter of the Chip Design framework.
Your task is to read the design specification of an SoC and produce a structured JSON file describing the intended architecture.
Your output must always follow the exact JSON schema described below.

Strict Output Requirements
- You must output ONLY valid JSON. No explanations, no comments, no markdown, no extra text.
- All field names must match the schema exactly.
- All strings must be double-quoted.
- If information is missing in the specification, assign an empty list [] or an empty string "".
- Do not infer RTL-level details. Only extract what the specification explicitly states.
- If an item does not exist, do NOT create one.
- Translate any Chinese content in the specification to English for the output.

JSON Schema to Follow
You must output a single JSON object representing the Top Level Module, with the following recursive structure:

{
  "Module_name": "string",   // Name of the module
  "Instance_name": "string", // Name of the instance (use "Top" for the root)
  "Port": [                  // List of ports
    "port_name",             // For top level ports
    "port_name : signal"     // For submodules, describing connections
  ],
  "Instances": [             // List of sub-instances
    {
      "Module_name": "string",
      "Instance_name": "string",
      "Port": ["..."],
      "Instances": [...]     // Recursive structure
    }
  ]
}

Rules for Extraction
- Use the specification hierarchy to determine modules.
- If a high-level block contains sub-components, list them in "Instances".
- For "Port" in submodules, try to capture the connection format "port_name : signal_name" if described.
- Never guess unspecified parameters or undeclared ports.

Validation Before Output
- Ensure the JSON parses without error.
- Ensure all lists are present even if empty.
- Ensure no trailing commas exist.
- Ensure the schema is followed exactly.

Final Output Rule
Output only the JSON object. Do not include any other text.
"""

def parse_spec(spec_file, api_key=None, model="gpt-5",output_file='SPEC.json'):
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set.")
            print("Please set it via 'export OPENAI_API_KEY=your_key' or pass it with --key.")
            return

    if not os.path.exists(spec_file):
        print(f"Error: File '{spec_file}' not found.")
        return

    try:
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_content = f.read()
    except Exception as e:
        print(f"Error reading file {spec_file}: {e}")
        return

    print(f"Parsing {spec_file} using {model}...")
    
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": spec_content}
            ],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        try:
            cleaned_content = content
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            
            cleaned_content = cleaned_content.strip()
            
            json_obj = json.loads(cleaned_content)
            
            print(json.dumps(json_obj, indent=2))
            
            # output_file = os.path.splitext(spec_file)[0] + "SPEC.json"
            with open(output_file, 'w') as f:
                json.dump(json_obj, f, indent=2)
            print(f"\nJSON saved to {output_file}")
            
        except json.JSONDecodeError as e:
            print(f"Error: LLM did not return valid JSON. Raw output:\n{content}")
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")

def main():
    spec_file = '../docs/spec.md'
    parse_spec(spec_file)

if __name__ == "__main__":
    main()
