#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import os
import json
from collections import defaultdict

def parse_xml_module_hierarchy(xml_file):
    print(f"Parsing file: {xml_file}")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file: {e}")
        return None
    
    module_hierarchy = {}
    module_ports = {}

    file_map = {}
    for file_node in root.findall('.//files/file'):
        file_map[file_node.get('id')] = file_node.get('filename')
    
    top_modules = set()
    for module in root.findall('.//module'):
        if module.get('topModule') == '1':
            top_modules.add(module.get('name'))
    
    for module in root.findall('.//module'):
        module_name = module.get('name')
        
        loc = module.get('loc')
        file_path = ""
        if loc:
            file_id = loc.split(',')[0]
            file_path = file_map.get(file_id, "")

        module_hierarchy[module_name] = {
            'submodules': [],
            'ports': [],
            'top': module_name in top_modules,
            'file_path': file_path
        }
        
        for var in module.findall('./var'):
            if var.get('dir') in ['input', 'output', 'inout']:
                module_ports[module_name] = module_ports.get(module_name, [])
                module_ports[module_name].append({
                    'name': var.get('name'),
                    'direction': var.get('dir'),
                    'type': var.get('vartype')
                })
    
    for module in root.findall('.//module'):
        module_name = module.get('name')
        
        for instance in module.findall('./instance'):
            instance_name = instance.get('name')
            instance_type = instance.get('defName')
            
            if module_name in module_hierarchy:
                module_hierarchy[module_name]['submodules'].append({
                    'name': instance_name,
                    'type': instance_type
                })
                
                connections = []
                for port in instance.findall('./port'):
                    port_name = port.get('name')
                    port_dir = port.get('direction')
                    
                    connected_signals = []
                    for varref in port.findall('./varref'):
                        connected_signals.append(varref.get('name'))
                    
                    connections.append({
                        'port': port_name,
                        'direction': port_dir,
                        'connected_to': connected_signals
                    })
                
                module_hierarchy[module_name]['connections'] = module_hierarchy[module_name].get('connections', {})
                module_hierarchy[module_name]['connections'][instance_name] = connections
    
    return {
        'hierarchy': module_hierarchy,
        'ports': module_ports,
        'top_modules': list(top_modules)
    }

def print_module_hierarchy(hierarchy_data, module_name, level=0, indent=""):
    if level == 0:
        print(f"{module_name}")
        indent = ""
    
    if module_name not in hierarchy_data['hierarchy']:
        return
    
    module_info = hierarchy_data['hierarchy'][module_name]
    submodules = module_info['submodules']
    
    for submodule in submodules:
        submodule_name = submodule['name']
        submodule_type = submodule['type']
        
        if submodule == submodules[-1]:
            print(f"{indent}└── {submodule_name}({submodule_type})")
        else:
            print(f"{indent}├── {submodule_name}({submodule_type})")
        
        if submodule_type in hierarchy_data['hierarchy']:
            if submodule == submodules[-1]:
                new_indent = indent + "    "
            else:
                new_indent = indent + "│   "
            print_module_hierarchy(hierarchy_data, submodule_type, level+1, new_indent)

def export_hierarchy_to_file(hierarchy_data, top_module, output_file, ports_file):
    original_stdout = sys.stdout
    with open(output_file, 'w') as f:
        sys.stdout = f
        print_module_hierarchy(hierarchy_data, top_module)
    sys.stdout = original_stdout
    print(f"Module hierarchy saved to {output_file}")
    
    with open(ports_file, 'w') as f:
        for module_name, module_info in hierarchy_data['hierarchy'].items():
            f.write(f"Module: {module_name}\n")
            f.write("="*50 + "\n")
            
            if module_name in hierarchy_data['ports']:
                f.write("Ports:\n")
                for port in hierarchy_data['ports'][module_name]:
                    f.write(f"  {port['direction']}: {port['name']} ({port['type']})\n")
            
            if 'connections' in module_info:
                f.write("\nConnections:\n")
                for submodule_name, connections in module_info['connections'].items():
                    f.write(f"  Submodule: {submodule_name}\n")
                    for conn in connections:
                        connected_to = ', '.join(conn['connected_to'])
                        f.write(f"    {conn['port']} ({conn['direction']}) -> {connected_to}\n")
            
            f.write("\n\n")
    
    print(f"Port connections saved to {ports_file}")

def export_hierarchy_to_dot(hierarchy_data, top_module, output_file):
    with open(output_file, 'w') as f:
        f.write('digraph ModuleHierarchy {\n')
        f.write('  rankdir=LR;\n')  
        f.write('  node [shape=box, style=filled, fillcolor=lightblue];\n\n')
        
        visited = set()
        
        def add_module_nodes(module_name, parent=None):
            if module_name in visited:
                return
            
            visited.add(module_name)
            label = f"{module_name}"
            f.write(f'  "{module_name}" [label="{label}"];\n')
            if parent:
                f.write(f'  "{parent}" -> "{module_name}";\n')
            
            if module_name in hierarchy_data['hierarchy']:
                for submodule in hierarchy_data['hierarchy'][module_name]['submodules']:
                    submodule_type = submodule['type']
                    submodule_name = submodule['name']
                    instance_name = f"{module_name}.{submodule_name}"
                    
                    instance_label = f"{submodule_name}\\n({submodule_type})"
                    f.write(f'  "{instance_name}" [label="{instance_label}", shape=ellipse, fillcolor=lightgreen];\n')
                    f.write(f'  "{module_name}" -> "{instance_name}" [style=dashed];\n')
                    f.write(f'  "{instance_name}" -> "{submodule_type}" [label=" "];\n')
                    
                    add_module_nodes(submodule_type)
        
        add_module_nodes(top_module)
        f.write('}\n')
    
    print(f"Module hierarchy DOT file exported to {output_file}")
    print(f"Visualize with Graphviz: dot -Tpng {output_file} -o {output_file.replace('.dot', '.png')}")

def export_nested_hierarchy_to_dot(hierarchy_data, top_module, output_file):
    with open(output_file, 'w') as f:
        f.write('digraph ModuleHierarchy {\n')
        f.write('  rankdir=TB;\n')
        f.write('  compound=true;\n')
        f.write('  node [shape=box, style=filled, fillcolor=lightblue];\n\n')
        
        visited = set()
        
        def add_nested_module(module_name, cluster_id=None):
            if module_name in visited:
                return
            
            visited.add(module_name)
            current_cluster = f"cluster_{module_name}"
            f.write(f'  subgraph "{current_cluster}" {{\n')
            f.write(f'    label="{module_name}";\n')
            f.write(f'    style=filled;\n')
            f.write(f'    color=lightgrey;\n')
            f.write(f'    node [style=filled, fillcolor=white];\n')
            
            module_node_id = f"{module_name}_node"
            f.write(f'    "{module_node_id}" [label="{module_name}", shape=box, fillcolor=lightblue];\n')
            
            if module_name in hierarchy_data['hierarchy']:
                for submodule in hierarchy_data['hierarchy'][module_name]['submodules']:
                    submodule_type = submodule['type']
                    submodule_name = submodule['name']
                    instance_id = f"{module_name}_{submodule_name}"
                    
                    instance_label = f"{submodule_name}\\n({submodule_type})"
                    f.write(f'    "{instance_id}" [label="{instance_label}", shape=ellipse, fillcolor=lightgreen];\n')
                    f.write(f'    "{module_node_id}" -> "{instance_id}" [style=dashed];\n')
                
                f.write('  }\n\n')
                
                for submodule in hierarchy_data['hierarchy'][module_name]['submodules']:
                    submodule_type = submodule['type']
                    submodule_name = submodule['name']
                    instance_id = f"{module_name}_{submodule_name}"
                    
                    if submodule_type in hierarchy_data['hierarchy'] and submodule_type not in visited:
                        add_nested_module(submodule_type)
                    
                    if submodule_type in visited:
                        sub_node_id = f"{submodule_type}_node"
                        f.write(f'  "{instance_id}" -> "{sub_node_id}" [lhead="cluster_{submodule_type}"];\n')
            else:
                f.write('  }\n\n')
        
        add_nested_module(top_module)
        f.write('}\n')

def export_hierarchy_to_json(hierarchy_data, top_module, output_file):
    def build_structure(module_name, instance_name, connections=None):
        file_path = ""
        if module_name in hierarchy_data['hierarchy']:
             file_path = hierarchy_data['hierarchy'][module_name].get('file_path', "")

        node = {
            "Module_name": module_name,
            "Instance_name": instance_name,
            "File_path": file_path,
            "Port": [],
            "Instances": []
        }
        
        if connections is None:
            if module_name in hierarchy_data['ports']:
                node["Port"] = [p['name'] for p in hierarchy_data['ports'][module_name]]
        else:
            for conn in connections:
                connected_to = ', '.join(conn['connected_to'])
                node["Port"].append(f"{conn['port']} : {connected_to}")
        
        if module_name in hierarchy_data['hierarchy']:
            module_info = hierarchy_data['hierarchy'][module_name]
            module_connections = module_info.get('connections', {})
            
            for submodule in module_info['submodules']:
                sub_name = submodule['name']
                sub_type = submodule['type']
                sub_conns = module_connections.get(sub_name, [])
                
                child_node = build_structure(sub_type, sub_name, sub_conns)
                node["Instances"].append(child_node)
        
        return node

    json_data = build_structure(top_module, "Top")
    
    with open(output_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"JSON structure saved to {output_file}")

def run_extract(xml_file):
    base_name = os.path.splitext(os.path.basename(xml_file))[0]
    hierarchy_file = os.path.join('./', f"{base_name}_hierarchy.txt")
    ports_file = os.path.join('./', f"{base_name}_ports.txt")
    # output_dot_file = os.path.join('./', f"{base_name}_hierarchy.dot")
    # nested_dot_file = os.path.join('./', f"{base_name}_nested_hierarchy.dot")
    json_file = os.path.join('./', f"{base_name}_hierarchy.json")
    
    hierarchy_data = parse_xml_module_hierarchy(xml_file)
    
    if hierarchy_data:
        top_modules = hierarchy_data.get('top_modules', [])
        
        if not top_modules:
            all_modules = set(hierarchy_data['hierarchy'].keys())
            instantiated_modules = set()
            for module in hierarchy_data['hierarchy'].values():
                for submodule in module['submodules']:
                    instantiated_modules.add(submodule['type'])
            
            top_modules = list(all_modules - instantiated_modules)
            
            if not top_modules:
                module_prefix = base_name.replace('V', '', 1)
                top_candidates = [m for m in hierarchy_data['hierarchy'] if module_prefix.lower() in m.lower()]
                
                if top_candidates:
                    top_modules = top_candidates
                else:
                    top_modules = list(hierarchy_data['hierarchy'].keys())
        
        if top_modules:
            top_module = top_modules[0]
            print(f"Top module: {top_module}")
            
            export_hierarchy_to_file(hierarchy_data, top_module, hierarchy_file, ports_file)
            # export_hierarchy_to_dot(hierarchy_data, top_module, output_dot_file)
            # export_nested_hierarchy_to_dot(hierarchy_data, top_module, nested_dot_file)
            export_hierarchy_to_json(hierarchy_data, top_module, json_file)
            return True
        else:
            print("Could not determine top module")
            return False
    else:
        print("Failed to parse XML file")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <xml_file> [hierarchy_file] [ports_file]")
        print("Example: python extractor.py /path/to/VChipTop.xml")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    run_extract(xml_file)

if __name__ == "__main__":
    main()
