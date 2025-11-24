#!/usr/bin/env python3
import json
import argparse
import os
import sys

def load_json(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        sys.exit(1)

def normalize_port(port_str):
    return port_str.replace(" ", "")

def find_arch_diffs(spec_node, parsed_node, parent_file, diffs):
    s_mod = spec_node.get("Module_name", "")
    p_mod = parsed_node.get("Module_name", "")
    s_inst = spec_node.get("Instance_name", "")
    p_inst = parsed_node.get("Instance_name", "")
    
    s_ports = spec_node.get("Port", [])
    p_ports = parsed_node.get("Port", [])
    
    s_ports_norm = sorted([normalize_port(p) for p in s_ports])
    p_ports_norm = sorted([normalize_port(p) for p in p_ports])
    
    current_node_file = parsed_node.get("File_path", "")
    if not current_node_file:
        current_node_file = parent_file if parent_file else "Top Level"

    if s_mod != p_mod or s_ports_norm != p_ports_norm:
        diffs.append({
            "file": current_node_file,
            "SPEC": {
                "Module_name": s_mod,
                "Instance_name": s_inst,
                "Port": s_ports
            },
            "Parsed": {
                "Module_name": p_mod,
                "Instance_name": p_inst,
                "Port": p_ports
            }
        })
    
    s_children = spec_node.get("Instances", [])
    p_children = parsed_node.get("Instances", [])
    
    s_map = {c.get("Instance_name"): c for c in s_children}
    p_map = {c.get("Instance_name"): c for c in p_children}
    
    all_keys = set(s_map.keys()) | set(p_map.keys())
    
    current_file = parsed_node.get("File_path", "")
    if not current_file:
         current_file = f"{p_mod}.v" if p_mod else (f"{s_mod}.v" if s_mod else "Unknown.v")
    
    for key in all_keys:
        if key in s_map and key in p_map:
            find_arch_diffs(s_map[key], p_map[key], current_file, diffs)
        elif key in s_map:
            diffs.append({
                "file": current_file,
                "SPEC": {
                    "Module_name": s_map[key].get("Module_name", ""),
                    "Instance_name": key,
                    "Port": s_map[key].get("Port", [])
                },
                "Parsed": "Missing"
            })
        else:
            child_node = p_map[key]
            child_file = child_node.get("File_path", current_file)
            
            diffs.append({
                "file": child_file,
                "SPEC": "Missing",
                "Parsed": {
                    "Module_name": p_map[key].get("Module_name", ""),
                    "Instance_name": key,
                    "Port": p_map[key].get("Port", [])
                }
            })

def run_compare(spec_json, parsed_json, output_json):
    if not os.path.exists(spec_json):
        print(f"Warning: {spec_json} not found.")
    
    spec_data = load_json(spec_json)
    parsed_data = load_json(parsed_json)
    
    diffs = []
    
    find_arch_diffs(spec_data, parsed_data, None, diffs)
    
    output = {"Diff_Arch": diffs}
    
    with open(output_json, 'w') as f:
        json.dump(output, f, indent=2)
        
    print(f"Differences saved to {output_json}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Compare SPEC and Parsed JSON files.")
    parser.add_argument("spec_json", nargs='?', default='SPEC.json', help="Path to the SPEC JSON file")
    parser.add_argument("parsed_json", nargs='?', default='Vtop_hierarchy.json', help="Path to the Parsed JSON file")
    parser.add_argument("output_json", nargs='?', default='Diff_Arch.json', help="Path to the output JSON file")
    
    args = parser.parse_args()
    
    run_compare(args.spec_json, args.parsed_json, args.output_json)

if __name__ == "__main__":
    main()
