#!/usr/bin/env python3
import os
import json
import subprocess
import shutil
import sys
import time
import interpreter
import extractor
import comparator
from openai import OpenAI

MAX_ITER = 5
LOG_FILE = "./sim.log"
SPEC_JSON = "SPEC.json"
RTL_JSON = "Vtop_hierarchy.json"
DIFF_JSON = "Diff_Arch.json"

def run_cmd(cmd, redirect_output=None):
    print(f"Running: {cmd}")
    if redirect_output:
        with open(redirect_output, 'w') as f:
            ret = subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)
    else:
        ret = subprocess.call(cmd, shell=True)
    
    if ret != 0:
        print(f"Command failed: {cmd}")
        return False
    return True

def get_llm_fix(diff_entry, file_content, api_key, model="gpt-5"):    
    client = OpenAI(api_key=api_key)
    
    system_prompt = """You are an expert Verilog/SystemVerilog RTL engineer.
Your task is to fix mismatches between the Design Specification and the implemented RTL code.
You will be provided with:
1. The file path.
2. The current RTL code content.
3. A JSON object describing the difference (Expected SPEC vs Parsed RTL).

Your Goal:
Modify the RTL code to match the SPEC.
- Only change the parts necessary to resolve the mismatch (e.g., port names, module names, instance names).
- Preserve the rest of the logic.
- Output the FULL modified file content.
- Do not output markdown formatting like ```verilog ... ```, just the raw code.
"""
    
    user_prompt = f"""
File: {diff_entry.get('file')}

Difference Detected:
{json.dumps(diff_entry, indent=2)}

Current File Content:
{file_content}

Please provide the corrected full file content.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines)
            
        return content
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None

def step1_parse_spec():
    print("Step 1: Parsing Spec...")
    try:
        interpreter.parse_spec('../docs/spec.md',output_file=SPEC_JSON)
        return True
    except Exception as e:
        print(f"Error parsing spec: {e}")
        return False

def step2_parse_rtl():
    print("Step 2: Parsing RTL...")
    if not run_cmd("make xml"): 
        print("Failed to generate XML.")
        return False
    try:
        return extractor.run_extract('./work/obj_dir/Vtop.xml')
    except Exception as e:
        print(f"Error extracting RTL: {e}")
        return False

def step3_compare():
    print("Step 3: Comparing...")
    try:
        return comparator.run_compare(SPEC_JSON, RTL_JSON, DIFF_JSON)
    except Exception as e:
        print(f"Error comparing: {e}")
        return False

def check_sim_pass():
    if not os.path.exists(LOG_FILE):
        print(f"Log file {LOG_FILE} not found.")
        return False
    
    try:
        with open(LOG_FILE, 'r', errors='ignore') as f:
            content = f.read()
            if "sim passed" in content.lower() or "simulation passed" in content.lower():
                return True
    except Exception as e:
        print(f"Error reading log file: {e}")
    
    return False

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not set. LLM features will fail.")
    
    # Step 1: Parse Spec (Run once)
    if not step1_parse_spec():
        return

    for i in range(MAX_ITER):
        print(f"\n{'='*20} Iteration {i+1}/{MAX_ITER} {'='*20}")
        
        # Step 2: Parse RTL
        if not step2_parse_rtl():
            print("Aborting due to RTL parsing failure.")
            break
            
        # Step 3: Compare
        if not step3_compare():
            print("Aborting due to comparison failure.")
            break
            
        # Read Diffs
        if not os.path.exists(DIFF_JSON):
            print("Diff file not found.")
            break
            
        with open(DIFF_JSON, 'r') as f:
            data = json.load(f)
            diffs = data.get("Diff_Arch", [])
            
        if not diffs:
            print("No architectural differences found.")
            # Run simulation to confirm
            print("Running simulation...")
            run_cmd("make all", redirect_output=LOG_FILE)
            if check_sim_pass():
                print("SUCCESS: Simulation Passed!")
                break
            else:
                print("FAILURE: Simulation Failed despite no arch diffs.")
                break
        
        print(f"Found {len(diffs)} differences. Attempting fixes...")
        
        # Step 4: Fix Agent
        modified_files = []
        
        for diff in diffs:
            file_path = diff.get('file')
            if not file_path or not os.path.exists(file_path):
                print(f"Skipping invalid file path: {file_path}")
                continue
                
            print(f"Fixing file: {file_path}")
            
            # Read original content
            with open(file_path, 'r') as f:
                original_content = f.read()
            
            # Get fix from LLM
            new_content = get_llm_fix(diff, original_content, api_key)
            
            if new_content:
                # Backup original
                backup_path = file_path + ".bak"
                if not os.path.exists(backup_path):
                    shutil.copy(file_path, backup_path)
                    print(f"Backed up to {backup_path}")
                
                # Write new content
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                modified_files.append(file_path)
                print("Applied fix.")
            else:
                print("Failed to generate fix.")
        
        if not modified_files:
            print("No files were modified. Stopping.")
            break
            
        # Run Simulation
        print("Running simulation with modified files...")
        run_cmd("make all", redirect_output=LOG_FILE)
        
        if check_sim_pass():
            print("SUCCESS: Simulation Passed!")
            break
        else:
            print("Simulation Failed.")
            print("Protecting original files (backups already exist).")
            print("Recording modified paths:")
            for p in modified_files:
                print(f" - {p}")
            print("Continuing to next iteration to debug modified files...")

if __name__ == "__main__":
    main()
