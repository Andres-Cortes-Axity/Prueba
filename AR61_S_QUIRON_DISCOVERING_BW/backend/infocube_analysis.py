import streamlit as st
import networkx as nx
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import random
import math
from connectors.source_detectors import determine_infosource_type, get_source_system_info


def analyze_infocube_connections(self, cube_name, depth, include_all_sources, connection_types, show_lineage):
    """NEW METHOD: Analyze all connections for a specific InfoCube"""

    target_node = f"CUBE:{cube_name}"

    if target_node not in st.session_state.graph.nodes:
        return None

    # Find all connected objects including complete source tracing
    connected_objects = {}
    relationships_found = []
    visited_nodes = set()
    data_lineage_paths = []

    # Use BFS to find connections up to specified depth
    current_level = {target_node}

    for current_depth in range(depth):
        next_level = set()

        for node in current_level:
            if node in visited_nodes:
                continue

            visited_nodes.add(node)

            # Get all neighbors (both incoming and outgoing)
            neighbors = set()

            # Incoming connections (what feeds this InfoCube)
            for neighbor in st.session_state.graph.predecessors(node):
                edge_data = st.session_state.graph.get_edge_data(neighbor, node)
                if edge_data and edge_data.get('type') in connection_types:
                    neighbors.add(neighbor)
                    relationships_found.append({
                        'source': neighbor,
                        'target': node,
                        'direction': 'incoming',
                        'depth': current_depth + 1,
                        **edge_data
                    })

            # Outgoing connections (what uses this InfoCube)
            for neighbor in st.session_state.graph.successors(node):
                edge_data = st.session_state.graph.get_edge_data(node, neighbor)
                if edge_data and edge_data.get('type') in connection_types:
                    neighbors.add(neighbor)
                    relationships_found.append({
                        'source': node,
                        'target': neighbor,
                        'direction': 'outgoing',
                        'depth': current_depth + 1,
                        **edge_data
                    })

            # Enhanced source tracing for InfoCubes
            if include_all_sources:
                source_connections = trace_infocube_to_all_sources(self, node, current_depth + 1)
                for src_conn in source_connections:
                    if src_conn['source_node'] not in visited_nodes:
                        neighbors.add(src_conn['source_node'])
                        relationships_found.append({
                            'source': src_conn['source_node'],
                            'target': node,
                            'direction': 'incoming',
                            'depth': current_depth + 1,
                            'type': 'source_connection',
                            'source_system': src_conn.get('source_system', 'Unknown'),
                            'connection_path': src_conn.get('connection_path', [])
                        })

            next_level.update(neighbors)

        if next_level:
            current_level = next_level
        else:
            break

    # Generate data lineage paths if requested
    if show_lineage:
        data_lineage_paths = generate_infocube_data_lineage(self, target_node, visited_nodes)

    # Collect object details for all connected nodes
    for node_id in visited_nodes:
        if node_id == target_node:
            continue  # Skip the target InfoCube itself

        node_data = st.session_state.graph.nodes.get(node_id)
        if node_data:
            obj_type = node_data['type']
            if obj_type not in connected_objects:
                connected_objects[obj_type] = []

            # Add connection statistics
            connections_out = len(list(st.session_state.graph.successors(node_id)))
            connections_in = len(list(st.session_state.graph.predecessors(node_id)))

            object_info = node_data.copy()
            object_info.update({
                'node_id': node_id,
                'connections_out': connections_out,
                'connections_in': connections_in,
                'total_connections': connections_in + connections_out
            })

            # Add source system information for DataSources
            if obj_type == 'DS':
                object_info['source_system'] = get_source_system_info(self, node_data['name'])
                object_info['infosource_type'] = determine_infosource_type(self, node_data['name'])

            connected_objects[obj_type].append(object_info)

    return {
        'target_cube': cube_name,
        'connected_objects': connected_objects,
        'relationships': relationships_found,
        'data_lineage_paths': data_lineage_paths,
        'total_objects': sum(len(objects) for objects in connected_objects.values()),
        'total_relationships': len(relationships_found),
        'analysis_depth': depth,
        'includes_all_sources': include_all_sources,
        'lineage_analysis': show_lineage
    }


def trace_infocube_to_all_sources(self, node_id, depth):
    """NEW METHOD: Trace InfoCube connections to all possible sources"""

    source_connections = []

    # Direct DataSource connections
    for neighbor in st.session_state.graph.predecessors(node_id):
        neighbor_data = st.session_state.graph.nodes.get(neighbor)
        if neighbor_data and neighbor_data.get('type') == 'DS':
            edge_data = st.session_state.graph.get_edge_data(neighbor, node_id)
            source_connections.append({
                'source_node': neighbor,
                'target_node': node_id,
                'source_name': neighbor_data['name'],
                'source_type': 'DataSource/InfoSource',
                'connection_type': edge_data.get('type', 'direct') if edge_data else 'direct',
                'depth': depth,
                'source_system': get_source_system_info(self, neighbor_data['name']),
                'infosource_type': determine_infosource_type(self, neighbor_data['name']),
                'connection_path': [neighbor_data['name']]
            })

    # Indirect connections through other providers
    for neighbor in st.session_state.graph.predecessors(node_id):
        neighbor_data = st.session_state.graph.nodes.get(neighbor)
        if neighbor_data and neighbor_data.get('type') in ['ADSO', 'ODSO', 'TRAN']:
            # Look for DataSources connected to this intermediate object
            for ds_neighbor in st.session_state.graph.predecessors(neighbor):
                ds_data = st.session_state.graph.nodes.get(ds_neighbor)
                if ds_data and ds_data.get('type') == 'DS':
                    edge_data = st.session_state.graph.get_edge_data(ds_neighbor, neighbor)
                    source_connections.append({
                        'source_node': ds_neighbor,
                        'target_node': node_id,
                        'intermediate_node': neighbor,
                        'source_name': ds_data['name'],
                        'source_type': 'DataSource/InfoSource',
                        'connection_type': f"via_{neighbor_data.get('type_name', 'Provider')}",
                        'depth': depth + 1,
                        'source_system': get_source_system_info(self, ds_data['name']),
                        'infosource_type': determine_infosource_type(self, ds_data['name']),
                        'connection_path': [ds_data['name'], neighbor_data['name']]
                    })

    return source_connections


def generate_infocube_data_lineage(self, target_cube, visited_nodes):
    """NEW METHOD: Generate complete data lineage paths for InfoCube"""

    lineage_paths = []

    # Find all DataSources in the visited nodes
    datasources = []
    for node_id in visited_nodes:
        node_data = st.session_state.graph.nodes.get(node_id)
        if node_data and node_data.get('type') == 'DS':
            datasources.append(node_id)

    # For each DataSource, find path to target InfoCube
    for ds_node in datasources:
        paths = list(nx.all_simple_paths(st.session_state.graph, ds_node, target_cube, cutoff=5))

        for path in paths:
            path_info = {
                'source': ds_node.split(':')[1],  # Remove type prefix
                'target': target_cube.split(':')[1],
                'path_length': len(path),
                'intermediate_objects': []
            }

            # Add intermediate objects
            for i, node_id in enumerate(path[1:-1], 1):  # Skip source and target
                node_data = st.session_state.graph.nodes.get(node_id)
                if node_data:
                    path_info['intermediate_objects'].append({
                        'step': i,
                        'object_name': node_data['name'],
                        'object_type': node_data['type_name'],
                        'category': node_data['category']
                    })

            lineage_paths.append(path_info)

    return lineage_paths


def calculate_connection_percentages(self):
    """Calculate comprehensive connection percentage statistics - ENHANCED METHOD"""

    connection_stats = {
        'total_objects': 0,
        'connected_objects': 0,
        'isolated_objects': 0,
        'overall_connected_percentage': 0.0,
        'isolated_percentage': 0.0,
        'connection_level_distribution': {},
        'by_object_type': {},
        'average_connections': 0.0,
        'max_connections': 0,
        'most_connected_object': None
    }

    # Initialize connection level buckets
    connection_levels = {
        '0 (Isolated)': 0,
        '1-5': 0,
        '6-10': 0,
        '11-20': 0,
        '21-50': 0,
        '50+': 0
    }

    total_connections = 0
    max_connections = 0
    most_connected_object = None

    # Analyze each object type
    for obj_type, objects in st.session_state.global_inventory.items():
        type_stats = {
            'total': len(objects),
            'connected': 0,
            'isolated': 0,
            'connected_percentage': 0.0,
            'average_connections': 0.0,
            'total_connections': 0
        }

        for obj in objects:
            node_id = f"{obj_type}:{obj['name']}"
            connections = 0

            if node_id in st.session_state.graph.nodes:
                connections = st.session_state.graph.degree(node_id)

            # Update totals
            connection_stats['total_objects'] += 1
            total_connections += connections

            if connections > 0:
                connection_stats['connected_objects'] += 1
                type_stats['connected'] += 1
            else:
                connection_stats['isolated_objects'] += 1
                type_stats['isolated'] += 1

            # Update connection level distribution
            if connections == 0:
                connection_levels['0 (Isolated)'] += 1
            elif connections <= 5:
                connection_levels['1-5'] += 1
            elif connections <= 10:
                connection_levels['6-10'] += 1
            elif connections <= 20:
                connection_levels['11-20'] += 1
            elif connections <= 50:
                connection_levels['21-50'] += 1
            else:
                connection_levels['50+'] += 1

            # Track most connected object
            if connections > max_connections:
                max_connections = connections
                most_connected_object = {
                    'name': obj['name'],
                    'type': obj['type_name'],
                    'connections': connections
                }

            type_stats['total_connections'] += connections

        # Calculate type-specific percentages
        if type_stats['total'] > 0:
            type_stats['connected_percentage'] = (type_stats['connected'] / type_stats['total']) * 100
            type_stats['average_connections'] = type_stats['total_connections'] / type_stats['total']

        connection_stats['by_object_type'][obj_type] = type_stats

    # Calculate overall percentages
    if connection_stats['total_objects'] > 0:
        connection_stats['overall_connected_percentage'] = (
            connection_stats['connected_objects'] / connection_stats['total_objects']
        ) * 100
        connection_stats['isolated_percentage'] = (
            connection_stats['isolated_objects'] / connection_stats['total_objects']
        ) * 100
        connection_stats['average_connections'] = total_connections / connection_stats['total_objects']

    connection_stats['connection_level_distribution'] = connection_levels
    connection_stats['max_connections'] = max_connections
    connection_stats['most_connected_object'] = most_connected_object

    return connection_stats


def prepare_infocube_connection_csv(self, results):
    """NEW METHOD: Prepare CSV export for InfoCube connection analysis"""

    csv_data = []

    # Header info
    csv_data.append("InfoCube Connection Analysis Report")
    csv_data.append(f"Target InfoCube,{results['target_cube']}")
    csv_data.append(f"Analysis Date,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    csv_data.append(f"Total Connected Objects,{results['total_objects']}")
    csv_data.append(f"Total Relationships,{results['total_relationships']}")
    csv_data.append(f"Analysis Depth,{results['analysis_depth']}")
    csv_data.append(f"Includes All Sources,{results['includes_all_sources']}")
    csv_data.append("")

    # Data lineage paths
    if results.get('data_lineage_paths'):
        csv_data.append("Data Lineage Paths")
        csv_data.append("Source,Source System,Target,Path Length,Intermediate Objects")

        for path in results['data_lineage_paths']:
            intermediate_names = [obj['object_name'] for obj in path['intermediate_objects']]
            intermediate_str = ' -> '.join(intermediate_names) if intermediate_names else 'Direct'
            source_system = get_source_system_info(self, path['source'])
            csv_data.append(f"{path['source']},{source_system},{path['target']},{path['path_length']},{intermediate_str}")

        csv_data.append("")

    # Connected objects
    csv_data.append("Connected Objects")
    csv_data.append("Object Name,Object Type,Category,Owner,InfoArea,In Connections,Out Connections,Total Connections,Source System,InfoSource Type")

    for obj_type, objects in results['connected_objects'].items():
        for obj in objects:
            source_system = obj.get('source_system', '') if obj_type == 'DS' else ''
            infosource_type = obj.get('infosource_type', '') if obj_type == 'DS' else ''
            csv_data.append(f"{obj['name']},{obj['type_name']},{obj['category']},{obj.get('owner', 'Unknown')},"
                            f"{obj.get('infoarea', 'UNASSIGNED')},{obj['connections_in']},{obj['connections_out']},"
                            f"{obj['total_connections']},{source_system},{infosource_type}")

    csv_data.append("")

    # Relationships
    csv_data.append("Relationships")
    csv_data.append("Source Object,Target Object,Connection Type,Direction,Depth,Source System")

    for rel in results['relationships']:
        source_name = rel['source'].split(':')[1] if ':' in rel['source'] else rel['source']
        target_name = rel['target'].split(':')[1] if ':' in rel['target'] else rel['target']
        source_system = rel.get('source_system', '')
        csv_data.append(f"{source_name},{target_name},{rel['type']},{rel['direction']},{rel['depth']},{source_system}")

    return '\n'.join(csv_data)


def prepare_infocube_connection_csv_with_percentages(self, results, connection_stats):
    """Prepare CSV export for InfoCube connection analysis with connection percentages - ENHANCED METHOD"""

    csv_data = []

    # Enhanced header info with connection statistics
    csv_data.append("InfoCube Connection Analysis Report with Connection Percentages")
    csv_data.append(f"Target InfoCube,{results['target_cube']}")
    csv_data.append(f"Analysis Date,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    csv_data.append(f"Total Connected Objects,{results['total_objects']}")
    csv_data.append(f"Total Relationships,{results['total_relationships']}")
    csv_data.append(f"Analysis Depth,{results['analysis_depth']}")
    csv_data.append(f"Includes All Sources,{results['includes_all_sources']}")

    # Add overall connection statistics
    if connection_stats:
        overall_connection_rate = (sum(stats['connected'] for stats in connection_stats.values()) / sum(stats['total'] for stats in
                                                                                                        connection_stats.values())) * 100
        csv_data.append(f"Overall Connection Rate,{overall_connection_rate:.1f}%")

    csv_data.append("")

    # Connection statistics by object type
    csv_data.append("Connection Statistics by Object Type")
    csv_data.append("Object Type,Total Objects,Connected Objects,Connection Rate %,Average Connections")

    for obj_type, stats in connection_stats.items():
        config = self.object_types[obj_type]
        avg_connections = sum(obj.get('total_connections', 0) for obj in
                              results['connected_objects'].get(obj_type, [])) / stats['total'] if stats['total'] > 0 else 0
        csv_data.append(f"{config['name']},{stats['total']},{stats['connected']},{stats['percentage']:.1f}%,{avg_connections:.1f}")

    csv_data.append("")

    # Data lineage paths with connection analysis
    if results.get('data_lineage_paths'):
        csv_data.append("Data Lineage Paths with Connection Analysis")
        csv_data.append("Source,Source System,Target,Path Length,Connection Complexity,Intermediate Objects")

        for path in results['data_lineage_paths']:
            intermediate_names = [obj['object_name'] for obj in path['intermediate_objects']]
            intermediate_str = ' -> '.join(intermediate_names) if intermediate_names else 'Direct'
            source_system = get_source_system_info(self, path['source'])
            complexity = "Simple" if path['path_length'] <= 2 else "Moderate" if path['path_length'] <= 4 else "Complex"
            csv_data.append(f"{path['source']},{source_system},{path['target']},{path['path_length']},{complexity},{intermediate_str}")

        csv_data.append("")

    # Enhanced connected objects with connection analysis
    csv_data.append("Connected Objects with Connection Analysis")
    csv_data.append("Object Name,Object Type,Category,Owner,InfoArea,In Connections,Out Connections,Total Connections,"
                    "Connection Status,Connection Rate in Type,Source System,InfoSource Type")

    for obj_type, objects in results['connected_objects'].items():
        for obj in objects:
            connection_status = 'Connected' if obj.get('total_connections', 0) > 0 else 'Isolated'

            # Calculate connection rate within type
            max_connections_in_type = max([o.get('total_connections', 0) for o in objects]) if objects else 1
            connection_rate_in_type = (obj.get('total_connections', 0) / max_connections_in_type * 100) if max_connections_in_type > 0 else 0

            source_system = obj.get('source_system', '') if obj_type == 'DS' else ''
            infosource_type = obj.get('infosource_type', '') if obj_type == 'DS' else ''

            csv_data.append(f"{obj['name']},{obj['type_name']},{obj['category']},{obj.get('owner', 'Unknown')},"
                            F"{obj.get('infoarea', 'UNASSIGNED')},{obj['connections_in']},{obj['connections_out']},"
                            F"{obj['total_connections']},{connection_status},{connection_rate_in_type:.1f}%,{source_system},{infosource_type}")

    csv_data.append("")

    # Enhanced relationships with connection context
    csv_data.append("Relationships with Connection Context")
    csv_data.append("Source Object,Target Object,Connection Type,Direction,Depth,Source Connections,Target Connections,Source System")

    for rel in results['relationships']:
        source_name = rel['source'].split(':')[1] if ':' in rel['source'] else rel['source']
        target_name = rel['target'].split(':')[1] if ':' in rel['target'] else rel['target']

        # Get connection counts for source and target
        source_connections = st.session_state.graph.degree(rel['source']) if rel['source'] in st.session_state.graph.nodes else 0
        target_connections = st.session_state.graph.degree(rel['target']) if rel['target'] in st.session_state.graph.nodes else 0

        source_system = rel.get('source_system', '')
        csv_data.append(f"{source_name},{target_name},{rel['type']},{rel['direction']},"
                        f"{rel['depth']},{source_connections},{target_connections},{source_system}")

    return '\n'.join(csv_data)


def generate_infocube_connection_report(self, cube_name, results):
    """NEW METHOD: Generate comprehensive text report for InfoCube connections"""

    report = f"""
═══════════════════════════════════════════════════════
    SAP BW INFOCUBE CONNECTION ANALYSIS REPORT
═══════════════════════════════════════════════════════

Target InfoCube: {cube_name}
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Depth: {results['analysis_depth']} levels
All Sources Included: {'Yes' if results.get('includes_all_sources', False) else 'No'}
Data Lineage Analysis: {'Yes' if results.get('lineage_analysis', False) else 'No'}

SUMMARY
-------
• Connected Objects: {results['total_objects']:,}
• Total Relationships: {results['total_relationships']:,}
• Data Lineage Paths: {len(results.get('data_lineage_paths', [])):,}

"""

    # Source system analysis
    if results['connected_objects'].get('DS'):
        source_summary = {}
        infosource_types = {}

        for ds_obj in results['connected_objects']['DS']:
            source_system = ds_obj.get('source_system', 'Unknown')
            infosource_type = ds_obj.get('infosource_type', 'DataSource')

            source_summary[source_system] = source_summary.get(source_system, 0) + 1
            infosource_types[infosource_type] = infosource_types.get(infosource_type, 0) + 1

        report += "SOURCE SYSTEM ANALYSIS\n"
        report += "---------------------\n"
        report += f"Total DataSources/InfoSources: {len(results['connected_objects']['DS'])}\n"
        report += f"Unique Source Systems: {len(source_summary)}\n\n"

        report += "Source Systems:\n"
        for system, count in sorted(source_summary.items(), key=lambda x: x[1], reverse=True):
            report += f"• {system}: {count} DataSources/InfoSources\n"

        report += "\nInfoSource Type Distribution:\n"
        for infosource_type, count in sorted(infosource_types.items(), key=lambda x: x[1], reverse=True):
            report += f"• {infosource_type}: {count}\n"

        report += "\n"

    # Data lineage analysis
    if results.get('data_lineage_paths'):
        report += "DATA LINEAGE ANALYSIS\n"
        report += "--------------------\n"
        report += f"Total Lineage Paths: {len(results['data_lineage_paths'])}\n"

        path_lengths = [path['path_length'] for path in results['data_lineage_paths']]
        if path_lengths:
            report += f"Average Path Length: {np.mean(path_lengths):.1f}\n"
            report += f"Shortest Path: {min(path_lengths)} steps\n"
            report += f"Longest Path: {max(path_lengths)} steps\n"
            report += f"Direct Connections: {len([p for p in results['data_lineage_paths'] if p['path_length'] == 2])}\n"

        report += "\nTop Data Sources (by connection paths):\n"
        source_path_counts = {}
        for path in results['data_lineage_paths']:
            source = path['source']
            source_path_counts[source] = source_path_counts.get(source, 0) + 1

        for source, count in sorted(source_path_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            source_system = get_source_system_info(self, source)
            report += f"• {source} ({source_system}): {count} path{'s' if count != 1 else ''}\n"

        report += "\n"

    # Object type breakdown
    report += "CONNECTION BREAKDOWN BY OBJECT TYPE\n"
    report += "----------------------------------\n"

    for obj_type, objects in results['connected_objects'].items():
        if objects:
            config = self.object_types[obj_type]
            report += f"\n{config['icon']} {config['name']}: {len(objects)} objects\n"

            # Enhanced display for DataSources
            if obj_type == 'DS':
                source_systems = set(obj.get('source_system', 'Unknown') for obj in objects)
                infosource_types = set(obj.get('infosource_type', 'DataSource') for obj in objects)
                report += f"  Source Systems: {', '.join(sorted(source_systems))}\n"
                report += f"  InfoSource Types: {', '.join(sorted(infosource_types))}\n"

            # List top 10 most connected objects
            sorted_objects = sorted(objects, key=lambda x: x.get('total_connections', 0), reverse=True)
            for obj in sorted_objects[:10]:
                connections_info = f"({obj.get('total_connections', 0)} connections)"
                if obj_type == 'DS':
                    source_sys = obj.get('source_system', 'Unknown')
                    infosource_type = obj.get('infosource_type', 'DS')
                    connections_info += f" - {source_sys} - {infosource_type}"
                report += f"  • {obj['name']} {connections_info}\n"

            if len(objects) > 10:
                report += f"  ... and {len(objects) - 10} more objects\n"

    # Connection flow analysis
    feeding_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'incoming')
    consuming_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'outgoing')
    source_connections = sum(1 for rel in results['relationships'] if rel.get('type') == 'source_connection')

    report += f"""

CONNECTION FLOW ANALYSIS
-----------------------
• Objects Feeding InfoCube: {feeding_count} (data sources)
• Objects Consuming from InfoCube: {consuming_count} (data consumers)
• Direct Source Connections: {source_connections} (DataSources/InfoSources)

INFOCUBE ASSESSMENT
------------------
"""

    if feeding_count > consuming_count:
        report += f"• DATA COLLECTOR: This InfoCube primarily collects data ({feeding_count} feeding connections)\n"
        report += "• Role: Central data repository for reporting and analysis\n"
        report += "• Consider: Performance optimization for data loading processes\n"
    elif consuming_count > feeding_count:
        report += f"• DATA PROVIDER: This InfoCube primarily provides data ({consuming_count} consuming connections)\n"
        report += "• Role: Data distribution hub for downstream processes\n"
        report += "• Consider: Impact analysis before structural changes\n"
    else:
        report += "• BALANCED PROCESSING: Equal data feeding and consuming\n"
        report += "• Role: Processing hub in data transformation chain\n"
        report += "• Consider: Standard maintenance and monitoring\n"

    # Source dependency analysis
    if results['connected_objects'].get('DS'):
        report += "\nSOURCE DEPENDENCY ANALYSIS:\n"
        unique_systems = set(obj.get('source_system', 'Unknown') for obj in results['connected_objects']['DS'])
        report += f"• Dependencies on {len(unique_systems)} source systems\n"
        report += f"• Source systems: {', '.join(sorted(unique_systems))}\n"

        if len(unique_systems) > 5:
            report += "• HIGH DEPENDENCY: Many source systems involved\n"
            report += "• Risk: Multiple points of failure\n"
            report += "• Recommendation: Implement robust monitoring\n"
        elif len(unique_systems) > 2:
            report += "• MODERATE DEPENDENCY: Multiple source systems\n"
            report += "• Recommendation: Monitor source system availability\n"
        else:
            report += "• LOW DEPENDENCY: Few source systems\n"
            report += "• Advantage: Simpler dependency management\n"

    # Recommendations
    report += f"""

RECOMMENDATIONS
--------------
• Monitor all {results['total_objects']} connected objects for changes
• Document the {len(results.get('data_lineage_paths', []))} data lineage paths
• Test impact on {consuming_count} downstream consumers before changes
• Verify data quality from {feeding_count} upstream sources
• Maintain relationships with {len(results['connected_objects'].get('DS', []))} DataSources/InfoSources
• Consider source system dependencies for availability planning

DATA QUALITY CHECKPOINTS
------------------------
"""

    if results.get('data_lineage_paths'):
        direct_paths = [p for p in results['data_lineage_paths'] if p['path_length'] == 2]
        indirect_paths = [p for p in results['data_lineage_paths'] if p['path_length'] > 2]

        report += f"• Direct data paths: {len(direct_paths)} (lower transformation risk)\n"
        report += f"• Indirect data paths: {len(indirect_paths)} (higher complexity)\n"

        if len(indirect_paths) > len(direct_paths):
            report += "• COMPLEX DATA FLOW: Many transformation steps\n"
            report += "• Recommendation: Implement comprehensive data validation\n"
        else:
            report += "• SIMPLE DATA FLOW: Mostly direct connections\n"
            report += "• Advantage: Lower data quality risk\n"

    report += """

═══════════════════════════════════════════════════════
                END OF REPORT
═══════════════════════════════════════════════════════
"""
    return report


def generate_infocube_connection_report_with_percentages(self, cube_name, results, connection_stats):
    """Generate comprehensive text report for InfoCube connections with connection percentages - ENHANCED METHOD"""

    # Calculate overall connection statistics
    overall_connected = sum(stats['connected'] for stats in connection_stats.values())
    overall_total = sum(stats['total'] for stats in connection_stats.values())
    overall_connection_rate = (overall_connected / overall_total * 100) if overall_total > 0 else 0

    report = f"""
═══════════════════════════════════════════════════════
SAP BW INFOCUBE CONNECTION ANALYSIS WITH PERCENTAGES
═══════════════════════════════════════════════════════

Target InfoCube: {cube_name}
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Depth: {results['analysis_depth']} levels
All Sources Included: {'Yes' if results.get('includes_all_sources', False) else 'No'}
Data Lineage Analysis: {'Yes' if results.get('lineage_analysis', False) else 'No'}

SUMMARY WITH CONNECTION ANALYSIS
-------------------------------
• Connected Objects: {results['total_objects']:,}
• Total Relationships: {results['total_relationships']:,}
• Data Lineage Paths: {len(results.get('data_lineage_paths', [])):,}
• Overall Connection Rate: {overall_connection_rate:.1f}%
• Connected Objects: {overall_connected:,} of {overall_total:,}

"""

    # Enhanced connection analysis by object type
    report += "CONNECTION ANALYSIS BY OBJECT TYPE\n"
    report += "----------------------------------\n"

    for obj_type, stats in sorted(connection_stats.items(), key=lambda x: x[1]['percentage'], reverse=True):
        config = self.object_types[obj_type]
        report += f"\n{config['icon']} {config['name']}:\n"
        report += f"  Total Objects: {stats['total']:,}\n"
        report += f"  Connected: {stats['connected']:,} ({stats['percentage']:.1f}%)\n"
        report += f"  Isolated: {stats['total'] - stats['connected']:,} ({100 - stats['percentage']:.1f}%)\n"

        # Add average connections
        if obj_type in results['connected_objects']:
            objects = results['connected_objects'][obj_type]
            avg_connections = sum(obj.get('total_connections', 0) for obj in objects) / len(objects) if objects else 0
            report += f"  Average Connections: {avg_connections:.1f}\n"

            # Connection distribution
            connected_objs = [obj for obj in objects if obj.get('total_connections', 0) > 0]
            if connected_objs:
                max_connections = max(obj.get('total_connections', 0) for obj in connected_objs)
                report += f"  Max Connections: {max_connections}\n"

            # Enhanced display for DataSources with source system analysis
            if obj_type == 'DS':
                source_systems = set(obj.get('source_system', 'Unknown') for obj in objects)
                infosource_types = set(obj.get('infosource_type', 'DataSource') for obj in objects)
                report += f"  Source Systems: {', '.join(sorted(source_systems))}\n"
                report += f"  InfoSource Types: {', '.join(sorted(infosource_types))}\n"

    # Enhanced data lineage analysis with connection insights
    if results.get('data_lineage_paths'):
        report += "\nDATA LINEAGE ANALYSIS WITH CONNECTION INSIGHTS\n"
        report += "---------------------------------------------\n"
        report += f"Total Lineage Paths: {len(results['data_lineage_paths'])}\n"

        path_lengths = [path['path_length'] for path in results['data_lineage_paths']]
        if path_lengths:
            direct_paths = [p for p in results['data_lineage_paths'] if p['path_length'] == 2]
            complex_paths = [p for p in results['data_lineage_paths'] if p['path_length'] > 3]

            report += f"Average Path Length: {np.mean(path_lengths):.1f}\n"
            report += f"Direct Connections: {len(direct_paths)} ({len(direct_paths) / len(results['data_lineage_paths']) * 100:.1f}%)\n"
            report += f"Complex Paths (>3 steps): {len(complex_paths)} ({len(complex_paths) / len(results['data_lineage_paths']) * 100:.1f}%)\n"

            # Connection complexity assessment
            direct_pct = (len(direct_paths) / len(results['data_lineage_paths'])) * 100
            if direct_pct > 70:
                report += "Connection Complexity: LOW - Mostly direct connections\n"
            elif direct_pct > 40:
                report += "Connection Complexity: MODERATE - Balanced connection patterns\n"
            else:
                report += "Connection Complexity: HIGH - Many indirect connection paths\n"

        # Source system connection analysis
        source_systems_analysis = {}
        for path in results['data_lineage_paths']:
            source_system = get_source_system_info(self, path['source'])
            if source_system not in source_systems_analysis:
                source_systems_analysis[source_system] = {'direct': 0, 'indirect': 0, 'total': 0}

            source_systems_analysis[source_system]['total'] += 1
            if path['path_length'] == 2:
                source_systems_analysis[source_system]['direct'] += 1
            else:
                source_systems_analysis[source_system]['indirect'] += 1

        report += "\nSource System Connection Patterns:\n"
        for system, analysis in sorted(source_systems_analysis.items(), key=lambda x: x[1]['total'], reverse=True):
            direct_pct = (analysis['direct'] / analysis['total'] * 100) if analysis['total'] > 0 else 0
            report += f"• {system}: {analysis['total']} paths ({direct_pct:.1f}% direct)\n"

    # Enhanced source system analysis
    if results['connected_objects'].get('DS'):
        report += "\nSOURCE SYSTEM ANALYSIS WITH CONNECTION RATES\n"
        report += "-------------------------------------------\n"

        source_summary = {}
        infosource_types = {}

        for ds_obj in results['connected_objects']['DS']:
            source_system = ds_obj.get('source_system', 'Unknown')
            infosource_type = ds_obj.get('infosource_type', 'DataSource')
            connections = ds_obj.get('total_connections', 0)

            if source_system not in source_summary:
                source_summary[source_system] = {'count': 0, 'connected': 0, 'total_connections': 0}
            source_summary[source_system]['count'] += 1
            source_summary[source_system]['total_connections'] += connections
            if connections > 0:
                source_summary[source_system]['connected'] += 1

            infosource_types[infosource_type] = infosource_types.get(infosource_type, 0) + 1

        report += f"Total DataSources/InfoSources: {len(results['connected_objects']['DS'])}\n"
        report += f"Unique Source Systems: {len(source_summary)}\n\n"

        report += "Source Systems with Connection Analysis:\n"
        for system, stats in sorted(source_summary.items(), key=lambda x: x[1]['count'], reverse=True):
            connection_rate = (stats['connected'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg_connections = stats['total_connections'] / stats['count'] if stats['count'] > 0 else 0
            report += f"• {system}:\n"
            report += f"  DataSources: {stats['count']}\n"
            report += f"  Connected: {stats['connected']} ({connection_rate:.1f}%)\n"
            report += f"  Avg Connections: {avg_connections:.1f}\n"

        report += "\nInfoSource Type Distribution:\n"
        for infosource_type, count in sorted(infosource_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(results['connected_objects']['DS'])) * 100
            report += f"• {infosource_type}: {count} ({percentage:.1f}%)\n"

    # Enhanced connection flow analysis
    feeding_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'incoming')
    consuming_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'outgoing')
    source_connections = sum(1 for rel in results['relationships'] if rel.get('type') == 'source_connection')

    report += f"""

CONNECTION FLOW ANALYSIS WITH PERCENTAGES
----------------------------------------
• Objects Feeding InfoCube: {feeding_count} ({feeding_count / results['total_relationships'] * 100:.1f}% of relationships)
• Objects Consuming from InfoCube: {consuming_count} ({consuming_count / results['total_relationships'] * 100:.1f}% of relationships)
• Direct Source Connections: {source_connections} ({source_connections / results['total_relationships'] * 100:.1f}% of relationships)

ENHANCED INFOCUBE ASSESSMENT
---------------------------
"""

    # Enhanced assessment with connection percentages
    if overall_connection_rate >= 80:
        report += f"• HIGHLY CONNECTED INFOCUBE ({overall_connection_rate:.1f}% connection rate)\n"
        report += "• Excellent integration with SAP BW landscape\n"
        report += "• Strong data flow patterns established\n"
    elif overall_connection_rate >= 60:
        report += f"• WELL CONNECTED INFOCUBE ({overall_connection_rate:.1f}% connection rate)\n"
        report += "• Good integration with most objects\n"
        report += "• Some isolated objects may need review\n"
    else:
        report += f"• LIMITED CONNECTION INFOCUBE ({overall_connection_rate:.1f}% connection rate)\n"
        report += "• Many objects lack proper integration\n"
        report += "• Consider reviewing data architecture\n"

    if feeding_count > consuming_count:
        report += f"• DATA COLLECTOR PATTERN: More feeding ({feeding_count}) than consuming ({consuming_count})\n"
        report += "• Role: Central data repository for reporting and analysis\n"
        report += "• Consider: Performance optimization for data loading processes\n"
    elif consuming_count > feeding_count:
        report += f"• DATA PROVIDER PATTERN: More consuming ({consuming_count}) than feeding ({feeding_count})\n"
        report += "• Role: Data distribution hub for downstream processes\n"
        report += "• Consider: Impact analysis before structural changes\n"
    else:
        report += "• BALANCED PROCESSING PATTERN: Equal feeding and consuming\n"
        report += "• Role: Processing hub in data transformation chain\n"
        report += "• Consider: Standard maintenance and monitoring\n"

    # Enhanced recommendations with connection insights
    report += f"""

ENHANCED RECOMMENDATIONS BASED ON CONNECTION ANALYSIS
--------------------------------------------------
• Monitor all {results['total_objects']} connected objects for changes
• Focus on {overall_connected} connected objects for impact analysis
• Document the {len(results.get('data_lineage_paths', []))} data lineage paths
• Test impact on {consuming_count} downstream consumers before changes
• Verify data quality from {feeding_count} upstream sources
• Maintain relationships with {len(results['connected_objects'].get('DS', []))} DataSources/InfoSources

CONNECTION-SPECIFIC RECOMMENDATIONS
---------------------------------
"""

    # Add connection-specific recommendations
    low_connection_types = [obj_type for obj_type, stats in connection_stats.items() if stats['percentage'] < 50]
    if low_connection_types:
        report += f"• REVIEW LOW CONNECTION TYPES: {', '.join([self.object_types[t]['name'] for t in low_connection_types])}\n"
        report += "• These object types have low connection rates and may need integration review\n"

    high_connection_types = [obj_type for obj_type, stats in connection_stats.items() if stats['percentage'] > 90]
    if high_connection_types:
        report += f"• LEVERAGE HIGH CONNECTION TYPES: {', '.join([self.object_types[t]['name'] for t in high_connection_types])}\n"
        report += "• These object types show excellent connectivity patterns\n"

    if results.get('data_lineage_paths'):
        direct_paths = [p for p in results['data_lineage_paths'] if p['path_length'] == 2]
        if len(direct_paths) / len(results['data_lineage_paths']) < 0.5:
            report += "• SIMPLIFY DATA PATHS: Many indirect connections detected\n"
            report += "• Consider consolidating transformation logic for better performance\n"

    report += """

═══════════════════════════════════════════════════════
                END OF ENHANCED REPORT
═══════════════════════════════════════════════════════
"""

    return report


def create_infocube_connection_3d_visualization(self, objects, relationships, target_cube):
    """NEW METHOD: Create 3D visualization specifically for InfoCube connections"""

    if not objects:
        return None

    # Create a focused graph
    focused_graph = nx.DiGraph()

    # Add nodes
    for obj in objects:
        focused_graph.add_node(obj['node_id'], **obj)

    # Add edges
    for rel in relationships:
        if rel['source'] in focused_graph.nodes and rel['target'] in focused_graph.nodes:
            focused_graph.add_edge(rel['source'], rel['target'], **rel)

    # Calculate positions with InfoCube at center
    pos_3d = calculate_infocube_analysis_positions(self, focused_graph, f"CUBE:{target_cube}")

    # Create visualization
    fig = go.Figure()

    # Add edges with direction-based styling
    add_infocube_analysis_edges(self, fig, relationships, pos_3d)

    # Add nodes with special highlighting for InfoCube and sources
    add_infocube_analysis_nodes(self, fig, objects, pos_3d, target_cube)

    # Update layout
    fig.update_layout(
        title={
            'text': f'🧊 InfoCube Connection Analysis: {target_cube}',
            'x': 0.5,
            'font': {'size': 20, 'color': 'white'}
        },
        scene=dict(
            xaxis=dict(showgrid=True, gridcolor='rgba(100,100,100,0.3)', showticklabels=False, color='white'),
            yaxis=dict(showgrid=True, gridcolor='rgba(100,100,100,0.3)', showticklabels=False, color='white'),
            zaxis=dict(showgrid=True, gridcolor='rgba(100,100,100,0.3)', color='white'),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            bgcolor='black',
            aspectmode='cube'
        ),
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        width=1200,
        height=800,
        showlegend=True,
        legend=dict(bgcolor='rgba(0,0,0,0.8)', bordercolor='white', borderwidth=1, font=dict(color='white')),
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig


def calculate_infocube_analysis_positions(self, graph, target_node):
    """NEW METHOD: Calculate positions for InfoCube analysis with target at center"""

    pos_3d = {}

    if target_node not in graph.nodes:
        return pos_3d

    # Target InfoCube at center
    pos_3d[target_node] = {'x': 0, 'y': 0, 'z': 0}

    # Separate nodes by type and direction
    feeding_nodes = []  # Objects that feed data TO the InfoCube
    consuming_nodes = []  # Objects that use data FROM the InfoCube
    source_nodes = []  # DataSources/InfoSources
    other_nodes = []

    for node_id in graph.nodes():
        if node_id == target_node:
            continue

        node_data = graph.nodes[node_id]

        # Check if it's a DataSource (special positioning)
        if node_data.get('type') == 'DS':
            source_nodes.append(node_id)
        # Check if it feeds the InfoCube (incoming data)
        elif graph.has_edge(node_id, target_node):
            feeding_nodes.append(node_id)
        # Check if it consumes from the InfoCube (outgoing data)
        elif graph.has_edge(target_node, node_id):
            consuming_nodes.append(node_id)
        else:
            other_nodes.append(node_id)

    # Position DataSources/InfoSources (bottom layer, far back)
    position_nodes_in_circle(self, source_nodes, pos_3d, center_z=-5, radius=8, y_offset=0, z_offset=-2)

    # Position feeding nodes (left side, negative X)
    position_nodes_in_circle(self, feeding_nodes, pos_3d, center_z=-1, radius=6, x_offset=-6)

    # Position consuming nodes (right side, positive X)
    position_nodes_in_circle(self, consuming_nodes, pos_3d, center_z=1, radius=6, x_offset=6)

    # Position other connected nodes (around the top)
    position_nodes_in_circle(self, other_nodes, pos_3d, center_z=2, radius=8, y_offset=6)

    return pos_3d


def position_nodes_in_circle(self, nodes, pos_3d, center_z=0, radius=5, y_offset=0, x_offset=0, z_offset=0):
    """Enhanced positioning method with more control"""

    if not nodes:
        return

    angle_step = 2 * math.pi / len(nodes) if len(nodes) > 1 else 0

    for i, node_id in enumerate(nodes):
        if len(nodes) == 1:
            x = x_offset
            y = y_offset
        else:
            angle = i * angle_step
            x = radius * math.cos(angle) + x_offset
            y = radius * math.sin(angle) + y_offset

        z = center_z + z_offset

        # Add some random variation for better visualization
        x += random.uniform(-0.5, 0.5)
        y += random.uniform(-0.5, 0.5)
        z += random.uniform(-0.3, 0.3)

        pos_3d[node_id] = {'x': x, 'y': y, 'z': z}


def add_infocube_analysis_edges(self, fig, relationships, pos_3d):
    """NEW METHOD: Add edges for InfoCube analysis with enhanced styling"""

    # Group edges by direction and type
    feeding_edges = []  # Data feeding the InfoCube
    consuming_edges = []  # InfoCube data being consumed
    source_edges = []  # Source connections

    for rel in relationships:
        if rel['source'] in pos_3d and rel['target'] in pos_3d:
            edge_data = {
                'x0': pos_3d[rel['source']]['x'],
                'y0': pos_3d[rel['source']]['y'],
                'z0': pos_3d[rel['source']]['z'],
                'x1': pos_3d[rel['target']]['x'],
                'y1': pos_3d[rel['target']]['y'],
                'z1': pos_3d[rel['target']]['z']
            }

            if rel.get('type') == 'source_connection':
                source_edges.append(edge_data)
            elif rel['direction'] == 'incoming':
                feeding_edges.append(edge_data)
            else:
                consuming_edges.append(edge_data)

    # Add feeding edges (green - data coming into InfoCube)
    if feeding_edges:
        edge_x, edge_y, edge_z = [], [], []
        for edge in feeding_edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#00FF7F', width=4),  # Bright green
            opacity=0.8,
            name=f"⬅️ Data Feeding InfoCube ({len(feeding_edges)})",
            showlegend=True,
            hoverinfo='none'
        ))

    # Add consuming edges (red - data going from InfoCube)
    if consuming_edges:
        edge_x, edge_y, edge_z = [], [], []
        for edge in consuming_edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#FF6347', width=4),  # Bright red
            opacity=0.8,
            name=f"➡️ InfoCube Data Usage ({len(consuming_edges)})",
            showlegend=True,
            hoverinfo='none'
        ))

    # Add source connection edges (blue - from DataSources/InfoSources)
    if source_edges:
        edge_x, edge_y, edge_z = [], [], []
        for edge in source_edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#00BFFF', width=6),  # Bright blue
            opacity=0.9,
            name=f"📡 Source Connections ({len(source_edges)})",
            showlegend=True,
            hoverinfo='none'
        ))


def add_infocube_analysis_nodes(self, fig, objects, pos_3d, target_cube):
    """NEW METHOD: Add nodes for InfoCube analysis with enhanced highlighting"""

    # Group objects
    target_objects = [obj for obj in objects if obj.get('is_target', False)]
    source_objects = [obj for obj in objects if obj.get('type') == 'DS']
    other_objects = [obj for obj in objects if not obj.get('is_target', False) and obj.get('type') != 'DS']

    # Add target InfoCube (special highlighting)
    if target_objects:
        obj = target_objects[0]
        node_id = obj['node_id']

        if node_id in pos_3d:
            pos = pos_3d[node_id]

            fig.add_trace(go.Scatter3d(
                x=[pos['x']], y=[pos['y']], z=[pos['z']],
                mode='markers+text',
                marker=dict(
                    size=45,  # Large size for target
                    color='#FFD700',  # Gold color
                    line=dict(width=5, color='white'),
                    opacity=1.0,
                    symbol='diamond'  # Diamond shape for InfoCube (cube not supported)
                ),
                text=[f"🧊<br>{obj['name']}"],
                textposition="middle center",
                textfont=dict(size=14, color='white', family="Arial Black"),
                hovertemplate=f"<b>🧊 TARGET INFOCUBE</b><br><b>{obj['name']}</b><br>Type: {obj['type_name']}<extra></extra>",
                name=f"🧊 Target: {target_cube}",
                showlegend=True
            ))

    # Add DataSource/InfoSource objects with enhanced information
    if source_objects:
        node_x, node_y, node_z = [], [], []
        node_sizes, node_text, node_info = [], [], []

        for obj in source_objects:
            node_id = obj['node_id']
            if node_id in pos_3d:
                pos = pos_3d[node_id]

                node_x.append(pos['x'])
                node_y.append(pos['y'])
                node_z.append(pos['z'])

                # Enhanced size for sources
                size = max(22, obj['size_base'] + obj.get('total_connections', 0) * 3)
                node_sizes.append(size)

                # Enhanced text with source system and InfoSource type
                display_name = obj['name'][:6] + '...' if len(obj['name']) > 6 else obj['name']
                source_sys = obj.get('source_system', 'Unknown')[:6]
                node_text.append(f"📡<br>{display_name}<br>({source_sys})")

                # Enhanced hover info
                info = f"<b>📡 {obj['name']}</b><br>"
                info += f"Type: {obj.get('infosource_type', 'DataSource')}<br>"
                info += f"Source System: {obj.get('source_system', 'Unknown')}<br>"
                info += f"Total Connections: {obj.get('total_connections', 0)}<br>"
                info += f"Owner: {obj.get('owner', 'Unknown')}<br>"
                info += f"InfoArea: {obj.get('infoarea', 'UNASSIGNED')}"
                node_info.append(info)

        if node_x:
            fig.add_trace(go.Scatter3d(
                x=node_x, y=node_y, z=node_z,
                mode='markers+text',
                marker=dict(
                    size=node_sizes,
                    color='#00BFFF',  # Bright blue for sources
                    line=dict(width=3, color='white'),
                    opacity=0.9,
                    symbol='triangle-up'
                ),
                text=node_text,
                textposition="middle center",
                textfont=dict(size=8, color='white', family="Arial Black"),
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=node_info,
                name=f"📡 DataSources/InfoSources ({len(source_objects)})",
                showlegend=True
            ))

    # Add other connected objects by category
    categories = set(obj['category'] for obj in other_objects)

    for category in categories:
        category_objects = [obj for obj in other_objects if obj['category'] == category]

        if not category_objects:
            continue

        node_x, node_y, node_z = [], [], []
        node_sizes, node_text, node_info = [], [], []

        for obj in category_objects:
            node_id = obj['node_id']
            if node_id in pos_3d:
                pos = pos_3d[node_id]

                node_x.append(pos['x'])
                node_y.append(pos['y'])
                node_z.append(pos['z'])

                # Node size based on connections
                size = max(15, obj['size_base'] + obj.get('total_connections', 0) * 2)
                node_sizes.append(size)

                # Node text
                display_name = obj['name'][:8] + '...' if len(obj['name']) > 8 else obj['name']
                node_text.append(f"{obj['icon']}<br>{display_name}")

                # Hover info
                info = f"<b>{obj['icon']} {obj['name']}</b><br>"
                info += f"Type: {obj['type_name']}<br>"
                info += f"Total Connections: {obj.get('total_connections', 0)}<br>"
                info += f"Owner: {obj.get('owner', 'Unknown')}<br>"
                info += f"InfoArea: {obj.get('infoarea', 'UNASSIGNED')}"
                node_info.append(info)

        if node_x:
            # Enhanced colors for visibility
            base_color = category_objects[0]['color']
            color_mapping = {
                '#FF6B6B': '#FF4444',  # Brighter red
                '#4ECDC4': '#00FFFF',  # Bright cyan
                '#45B7D1': '#1E90FF',  # Bright blue
                '#96CEB4': '#00FF7F',  # Bright green
                '#FFEAA7': '#FFD700',  # Gold
                '#DDA0DD': '#DA70D6'   # Bright orchid
            }
            display_color = color_mapping.get(base_color, base_color)

            fig.add_trace(go.Scatter3d(
                x=node_x, y=node_y, z=node_z,
                mode='markers+text',
                marker=dict(
                    size=node_sizes,
                    color=display_color,
                    line=dict(width=2, color='white'),
                    opacity=0.9
                ),
                text=node_text,
                textposition="middle center",
                textfont=dict(size=8, color='white', family="Arial Black"),
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=node_info,
                name=f"{category} ({len(category_objects)})",
                showlegend=True
            ))
