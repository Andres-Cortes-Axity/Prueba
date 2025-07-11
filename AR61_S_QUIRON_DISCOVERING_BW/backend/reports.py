import streamlit as st
from datetime import datetime
from connectors.source_detectors import get_source_system_info, determine_infosource_type


def generate_search_connection_summary(self, df, connection_filter_type):
    """Generate connection analysis summary for search results - NEW METHOD"""
    
    summary = f"""
═══════════════════════════════════════════════════════
    SAP BW OBJECT SEARCH CONNECTION ANALYSIS
═══════════════════════════════════════════════════════

Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Connection Filter: {connection_filter_type}
Total Results: {len(df):,}

CONNECTION ANALYSIS
------------------
"""
    
    # Connection statistics
    connected_count = len(df[df['Connection Status'] == 'Connected'])
    isolated_count = len(df[df['Connection Status'] == 'Isolated'])
    
    if len(df) > 0:
        connected_pct = (connected_count / len(df)) * 100
        isolated_pct = (isolated_count / len(df)) * 100
        
        summary += f"Connected Objects: {connected_count:,} ({connected_pct:.1f}%)\n"
        summary += f"Isolated Objects: {isolated_count:,} ({isolated_pct:.1f}%)\n"
        summary += f"Average Connections: {df['Connections'].mean():.1f}\n"
        summary += f"Maximum Connections: {df['Connections'].max()}\n"
        summary += f"Minimum Connections: {df['Connections'].min()}\n\n"
        
        # Type distribution
        summary += "OBJECT TYPE DISTRIBUTION\n"
        summary += "-----------------------\n"
        type_counts = df['Type'].value_counts()
        for obj_type, count in type_counts.items():
            percentage = (count / len(df)) * 100
            summary += f"{obj_type}: {count:,} ({percentage:.1f}%)\n"
        
        summary += "\n"
        
        # Top connected objects
        summary += "MOST CONNECTED OBJECTS\n"
        summary += "---------------------\n"
        top_connected = df.nlargest(10, 'Connections')
        for _, row in top_connected.iterrows():
            summary += f"{row['Name']} ({row['Type']}): {row['Connections']} connections\n"
        
        # Category analysis
        summary += "\nCATEGORY DISTRIBUTION\n"
        summary += "--------------------\n"
        category_counts = df['Category'].value_counts()
        for category, count in category_counts.items():
            percentage = (count / len(df)) * 100
            summary += f"{category}: {count:,} ({percentage:.1f}%)\n"
    
    summary += """

RECOMMENDATIONS
--------------
• Focus on highly connected objects for impact analysis
• Review isolated objects for potential cleanup
• Use InfoCube/InfoObject Analysis for detailed dependency mapping
• Consider connection patterns when planning changes

═══════════════════════════════════════════════════════
                END OF SUMMARY
═══════════════════════════════════════════════════════
"""
    
    return summary


def generate_connection_analysis_report(self):
    """Generate detailed connection analysis report"""
    
    report = f"""
═══════════════════════════════════════════════════════
        SAP BW CONNECTION ANALYSIS REPORT
═══════════════════════════════════════════════════════

Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Objects: {st.session_state.dataset_stats['total_objects']:,}
Total Relationships: {st.session_state.dataset_stats['total_relationships']:,}

CONNECTION TYPE ANALYSIS
-----------------------
"""
    
    # Analyze connection types
    connection_types = {}
    for rel in st.session_state.relationships:
        rel_type = rel['type']
        connection_types[rel_type] = connection_types.get(rel_type, 0) + 1
    
    for conn_type, count in sorted(connection_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(st.session_state.relationships)) * 100
        report += f"• {conn_type.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)\n"
    
    report += """

OBJECT CONNECTIVITY ANALYSIS
---------------------------
"""
    
    # Find most and least connected objects
    connectivity_stats = []
    for obj_type, objects in st.session_state.global_inventory.items():
        for obj in objects:
            node_id = f"{obj_type}:{obj['name']}"
            if node_id in st.session_state.graph.nodes:
                connections = st.session_state.graph.degree(node_id)
                connectivity_stats.append({
                    'name': obj['name'],
                    'type': obj['type_name'],
                    'connections': connections
                })
    
    # Sort by connections
    connectivity_stats.sort(key=lambda x: x['connections'], reverse=True)
    
    report += "Most Connected Objects:\n"
    for obj in connectivity_stats[:10]:
        report += f"• {obj['name']} ({obj['type']}): {obj['connections']} connections\n"
    
    report += f"\nIsolated Objects (0 connections): {sum(1 for obj in connectivity_stats if obj['connections'] == 0)}\n"
    
    # Source system analysis
    ds_objects = st.session_state.global_inventory.get('DS', [])
    if ds_objects:
        report += f"""

SOURCE SYSTEM ANALYSIS
---------------------
Total DataSources/InfoSources: {len(ds_objects)}

"""
        source_systems = {}
        infosource_types = {}
        
        for ds_obj in ds_objects:
            source_system = get_source_system_info(self, ds_obj['name'])
            infosource_type = determine_infosource_type(self, ds_obj['name'])
            
            source_systems[source_system] = source_systems.get(source_system, 0) + 1
            infosource_types[infosource_type] = infosource_types.get(infosource_type, 0) + 1
        
        report += "Source Systems:\n"
        for system, count in sorted(source_systems.items(), key=lambda x: x[1], reverse=True):
            report += f"• {system}: {count} DataSources\n"
        
        report += "\nInfoSource Types:\n"
        for infosource_type, count in sorted(infosource_types.items(), key=lambda x: x[1], reverse=True):
            report += f"• {infosource_type}: {count}\n"
    
    report += """

RECOMMENDATIONS
--------------
• Focus on InfoCube Connection Analysis for detailed dependency mapping
• Monitor highly connected objects for performance impact
• Document source system dependencies for availability planning
• Use InfoObject Impact Analysis for change impact assessment

═══════════════════════════════════════════════════════
                END OF REPORT
═══════════════════════════════════════════════════════
"""
    
    return report


def prepare_objects_csv_export(self):
    """Prepare comprehensive CSV export of all objects"""
    
    csv_data = []
    
    # Header
    csv_data.append("Object Name,Object Type,Category,Owner,InfoArea,Active,Status,Total Connections,"
                    "In Connections,Out Connections,Source System,InfoSource Type,Last Changed")
    
    # Process all objects
    for obj_type, objects in st.session_state.global_inventory.items():
        for obj in objects:
            node_id = f"{obj_type}:{obj['name']}"
            
            # Get connection statistics
            total_connections = 0
            in_connections = 0
            out_connections = 0
            
            if node_id in st.session_state.graph.nodes:
                total_connections = st.session_state.graph.degree(node_id)
                in_connections = st.session_state.graph.in_degree(node_id)
                out_connections = st.session_state.graph.out_degree(node_id)
            
            # Enhanced info for DataSources
            source_system = ""
            infosource_type = ""
            if obj_type == 'DS':
                source_system = get_source_system_info(self, obj['name'])
                infosource_type = determine_infosource_type(self, obj['name'])
            
            # Build CSV row
            row = [
                obj['name'],
                obj['type_name'],
                obj['category'],
                obj.get('owner', 'Unknown'),
                obj.get('infoarea', 'UNASSIGNED'),
                obj.get('active', 'Unknown'),
                obj.get('status', 'Unknown'),
                str(total_connections),
                str(in_connections),
                str(out_connections),
                source_system,
                infosource_type,
                obj.get('last_changed', 'Unknown')
            ]
            
            csv_data.append(','.join(f'"{field}"' for field in row))
    
    return '\n'.join(csv_data)


def get_sample_for_export(self):
    """Get a representative sample for export"""
    sample_objects = {}
    
    for obj_type, objects in st.session_state.global_inventory.items():
        if len(objects) > 100:
            # Take a sample of 100 most connected objects
            objects_with_connections = []
            for obj in objects:
                node_id = f"{obj_type}:{obj['name']}"
                connections = st.session_state.graph.degree(node_id) if node_id in st.session_state.graph.nodes else 0
                obj_copy = obj.copy()
                obj_copy['connections'] = connections
                objects_with_connections.append(obj_copy)
            
            # Sort by connections and take top 100
            objects_with_connections.sort(key=lambda x: x['connections'], reverse=True)
            sample_objects[obj_type] = objects_with_connections[:100]
        else:
            sample_objects[obj_type] = objects
