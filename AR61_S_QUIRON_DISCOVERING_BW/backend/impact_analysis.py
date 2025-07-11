import streamlit as st
import pandas as pd
import json
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime
from connectors.source_detectors import get_source_system_info
from backend.infocube_analysis import position_nodes_in_circle


def analyze_infoobject_impact_with_sources(self, iobj_name, depth, include_source_tracing, connection_types, show_source_systems):
    """Analyze impact for a specific InfoObject with enhanced source tracing"""

    target_node = f"IOBJ:{iobj_name}"

    if target_node not in st.session_state.graph.nodes:
        return None

    # Find all connected objects including source tracing
    connected_objects = {}
    relationships_found = []
    visited_nodes = set()
    source_connections = []

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

            # Outgoing connections (where this object is used)
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

            # Incoming connections (what uses this object)
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

            # Enhanced source tracing
            if include_source_tracing:
                source_info = trace_to_data_sources(self, node, current_depth + 1)
                if source_info:
                    source_connections.extend(source_info)
                    # Add DataSources to neighbors for continued analysis
                    for src_info in source_info:
                        if src_info['source_node'] not in visited_nodes:
                            neighbors.add(src_info['source_node'])

            next_level.update(neighbors)

        if next_level:
            current_level = next_level
        else:
            break

    # Collect object details for all connected nodes
    for node_id in visited_nodes:
        if node_id == target_node:
            continue  # Skip the target InfoObject itself

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

            # Add source system information if available
            if show_source_systems and obj_type == 'DS':
                object_info['source_system'] = get_source_system_info(self, node_data['name'])

            connected_objects[obj_type].append(object_info)

    return {
        'target_iobj': iobj_name,
        'connected_objects': connected_objects,
        'relationships': relationships_found,
        'source_connections': source_connections,
        'total_objects': sum(len(objects) for objects in connected_objects.values()),
        'total_relationships': len(relationships_found),
        'total_source_connections': len(source_connections),
        'analysis_depth': depth,
        'source_tracing_enabled': include_source_tracing
    }


def trace_to_data_sources(self, node_id, depth):
    """Trace connections back to DataSources"""

    source_connections = []

    # Look for transformation connections that lead to DataSources
    for neighbor in st.session_state.graph.predecessors(node_id):
        neighbor_data = st.session_state.graph.nodes.get(neighbor)
        if neighbor_data and neighbor_data.get('type') == 'DS':
            # Found a direct DataSource connection
            edge_data = st.session_state.graph.get_edge_data(neighbor, node_id)
            source_connections.append({
                'source_node': neighbor,
                'target_node': node_id,
                'source_name': neighbor_data['name'],
                'source_type': 'DataSource',
                'connection_type': edge_data.get('type', 'unknown') if edge_data else 'direct',
                'depth': depth,
                'source_system': get_source_system_info(self, neighbor_data['name'])
            })
        elif neighbor_data and neighbor_data.get('type') in ['ADSO', 'ODSO', 'CUBE']:
            # Check if this provider has DataSource connections
            for ds_neighbor in st.session_state.graph.predecessors(neighbor):
                ds_data = st.session_state.graph.nodes.get(ds_neighbor)
                if ds_data and ds_data.get('type') == 'DS':
                    edge_data = st.session_state.graph.get_edge_data(ds_neighbor, neighbor)
                    source_connections.append({
                        'source_node': ds_neighbor,
                        'target_node': node_id,
                        'intermediate_node': neighbor,
                        'source_name': ds_data['name'],
                        'source_type': 'DataSource',
                        'connection_type': f"via_{neighbor_data.get('type_name', 'Provider')}",
                        'depth': depth + 1,
                        'source_system': get_source_system_info(self, ds_data['name'])
                    })

    return source_connections


def display_impact_analysis_with_sources(self, iobj_name, results, group_by_type, show_details, render_3d):
    """Display the impact analysis results with source connection information"""

    # Summary metrics with source information
    st.success("✅ Impact Analysis with Source Tracing Complete!")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🎯 Target InfoObject", iobj_name)
    with col2:
        st.metric("🔗 Connected Objects", results['total_objects'])
    with col3:
        st.metric("↔️ Relationships", results['total_relationships'])
    with col4:
        st.metric("📡 Source Connections", results['total_source_connections'])
    with col5:
        st.metric("🔍 Analysis Depth", results['analysis_depth'])

    st.markdown("---")

    # Source connections analysis
    if results['source_connections']:
        st.subheader("📡 Data Source Connections")
        st.caption("Tracing back to original data sources and source systems")

        # Group source connections by source system
        source_by_system = {}
        for src_conn in results['source_connections']:
            system = src_conn.get('source_system', 'Unknown')
            if system not in source_by_system:
                source_by_system[system] = []
            source_by_system[system].append(src_conn)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📊 Source Systems Overview**")
            source_summary = []
            for system, connections in source_by_system.items():
                source_summary.append({
                    'Source System': system,
                    'DataSources': len(set(conn['source_name'] for conn in connections)),
                    'Connections': len(connections)
                })

            if source_summary:
                df_sources = pd.DataFrame(source_summary)
                st.dataframe(df_sources, use_container_width=True, height=200)

        with col2:
            st.markdown("**📡 DataSource Details**")
            datasource_details = []
            for src_conn in results['source_connections'][:10]:  # Show top 10
                datasource_details.append({
                    'DataSource': src_conn['source_name'],
                    'Source System': src_conn.get('source_system', 'Unknown'),
                    'Connection Type': src_conn['connection_type'],
                    'Depth': src_conn['depth']
                })

            if datasource_details:
                df_ds = pd.DataFrame(datasource_details)
                st.dataframe(df_ds, use_container_width=True, height=200)
                if len(results['source_connections']) > 10:
                    st.caption(f"Showing top 10 of {len(results['source_connections'])} source connections")

    st.markdown("---")

    # Connection direction analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Upstream Dependencies")
        st.caption("Objects that provide data TO this InfoObject")

        upstream_objects = []
        for rel in results['relationships']:
            if rel['direction'] == 'incoming':
                source_node = st.session_state.graph.nodes.get(rel['source'])
                if source_node:
                    upstream_objects.append({
                        'Object': source_node['name'],
                        'Type': source_node['type_name'],
                        'Connection Type': rel['type'].replace('_', ' ').title(),
                        'Depth': rel['depth']
                    })

        if upstream_objects:
            df_upstream = pd.DataFrame(upstream_objects)
            st.dataframe(df_upstream, use_container_width=True, height=200)
            st.caption(f"Showing {len(upstream_objects)} upstream dependencies")
        else:
            st.info("No upstream dependencies found")

    with col2:
        st.subheader("📉 Downstream Impact")
        st.caption("Objects that USE data FROM this InfoObject")

        downstream_objects = []
        for rel in results['relationships']:
            if rel['direction'] == 'outgoing':
                target_node = st.session_state.graph.nodes.get(rel['target'])
                if target_node:
                    downstream_objects.append({
                        'Object': target_node['name'],
                        'Type': target_node['type_name'],
                        'Connection Type': rel['type'].replace('_', ' ').title(),
                        'Depth': rel['depth']
                    })

        if downstream_objects:
            df_downstream = pd.DataFrame(downstream_objects)
            st.dataframe(df_downstream, use_container_width=True, height=200)
            st.caption(f"Showing {len(downstream_objects)} downstream impacts")
        else:
            st.info("No downstream impact found")

    st.markdown("---")

    # Detailed object analysis with source information
    if group_by_type:
        st.subheader("📊 Connected Objects by Type (with Source Info)")

        if not results['connected_objects']:
            st.warning("No connected objects found")
            return

        for obj_type, objects in results['connected_objects'].items():
            if not objects:
                continue

            config = self.object_types[obj_type]

            with st.expander(f"{config['icon']} {config['name']} ({len(objects)} objects)", expanded=True):

                if show_details:
                    # Enhanced detailed view with source information
                    detail_data = []
                    for obj in objects:
                        row_data = {
                            'Name': obj['name'],
                            'Owner': obj.get('owner', 'Unknown'),
                            'InfoArea': obj.get('infoarea', 'UNASSIGNED'),
                            'Active': obj.get('active', 'Unknown'),
                            'In Connections': obj['connections_in'],
                            'Out Connections': obj['connections_out'],
                            'Total Connections': obj['total_connections']
                        }

                        # Add source system info for DataSources
                        if obj_type == 'DS' and 'source_system' in obj:
                            row_data['Source System'] = obj['source_system']

                        detail_data.append(row_data)

                    df_detail = pd.DataFrame(detail_data)
                    df_detail = df_detail.sort_values('Total Connections', ascending=False)
                    st.dataframe(df_detail, use_container_width=True)

                else:
                    # Simple view with source system info for DataSources
                    if obj_type == 'DS':
                        object_display = []
                        for obj in objects:
                            source_sys = obj.get('source_system', 'Unknown')
                            object_display.append(f"{obj['name']} ({source_sys})")
                        st.write(", ".join(object_display))
                    else:
                        object_names = [obj['name'] for obj in objects]
                        st.write(", ".join(object_names))

    # 3D Visualization with source connections
    if render_3d and results['total_objects'] > 0:
        st.markdown("---")
        st.subheader("🎯 3D Impact Visualization with Source Connections")

        # Create focused dataset for visualization
        focused_objects = []

        # Add the target InfoObject
        target_iobj_data = None
        for obj in st.session_state.global_inventory.get('IOBJ', []):
            if obj['name'] == iobj_name:
                target_iobj_data = obj.copy()
                target_iobj_data['node_id'] = f"IOBJ:{iobj_name}"
                target_iobj_data['is_target'] = True
                break

        if target_iobj_data:
            focused_objects.append(target_iobj_data)

        # Add all connected objects
        for obj_type, objects in results['connected_objects'].items():
            for obj in objects:
                obj_copy = obj.copy()
                obj_copy['is_target'] = False
                focused_objects.append(obj_copy)

        # Create enhanced 3D visualization with source connections
        fig = create_impact_analysis_3d_visualization(
            self, focused_objects, results['relationships'], iobj_name
        )

        if fig:
            st.plotly_chart(fig, use_container_width=True, height=800)

            st.info("""
            🎮 **3D Impact Analysis Navigation:**
            - **🎯 Gold Diamond** = Target InfoObject
            - **⬅️ Green Lines** = Upstream dependencies
            - **➡️ Red Lines** = Downstream impact
            - **🔵 Blue Lines** = Source connections (to DataSources)
            - **📡 DataSource nodes** = Enhanced with source system info
            - **Node Size** = Reflects total connections
            - **Hover** for detailed object and source information
            """)

    # Export options with source information
    st.markdown("---")
    st.subheader("📤 Export Impact Analysis with Source Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        # CSV Export
        if st.button("📊 Export with Sources (CSV)"):
            csv_data = prepare_impact_analysis_csv_with_sources(self, results)
            st.download_button(
                label="📥 Download Impact Analysis with Sources (CSV)",
                data=csv_data,
                file_name=f"impact_analysis_sources_{iobj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    with col2:
        # JSON Export
        if st.button("📄 Export with Sources (JSON)"):
            json_data = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="📥 Download Impact Analysis with Sources (JSON)",
                data=json_data,
                file_name=f"impact_analysis_sources_{iobj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with col3:
        # Summary Report
        if st.button("📋 Generate Source Report"):
            report = generate_impact_analysis_report_with_sources(self, iobj_name, results)
            st.download_button(
                label="📥 Download Source Report (TXT)",
                data=report,
                file_name=f"impact_report_sources_{iobj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )


def create_impact_analysis_3d_visualization(self, objects, relationships, target_iobj):
    """Create 3D visualization for impact analysis"""

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

    # Calculate positions with target at center
    pos_3d = calculate_impact_analysis_positions(self, focused_graph, f"IOBJ:{target_iobj}")

    # Create visualization
    fig = go.Figure()

    # Add edges with direction-based styling
    add_impact_analysis_edges(self, fig, relationships, pos_3d)

    # Add nodes with special highlighting for target
    add_impact_analysis_nodes(self, fig, objects, pos_3d, target_iobj)

    # Update layout
    fig.update_layout(
        title={
            'text': f'🎯 InfoObject Impact Analysis: {target_iobj}',
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


def calculate_impact_analysis_positions(self, graph, target_node):
    """Calculate positions for impact analysis with target at center"""

    pos_3d = {}

    if target_node not in graph.nodes:
        return pos_3d

    # Target node at center
    pos_3d[target_node] = {'x': 0, 'y': 0, 'z': 0}

    # Separate nodes by type and direction
    upstream_nodes = []
    downstream_nodes = []
    other_nodes = []

    for node_id in graph.nodes():
        if node_id == target_node:
            continue

        # Check if it's upstream (provides data to target)
        if graph.has_edge(node_id, target_node):
            upstream_nodes.append(node_id)
        # Check if it's downstream (receives data from target)
        elif graph.has_edge(target_node, node_id):
            downstream_nodes.append(node_id)
        else:
            other_nodes.append(node_id)

    # Position upstream nodes (left side, negative Z)
    position_nodes_in_circle(self, upstream_nodes, pos_3d, center_z=-3, radius=6)

    # Position downstream nodes (right side, positive Z)
    position_nodes_in_circle(self, downstream_nodes, pos_3d, center_z=3, radius=6)

    # Position other connected nodes (around the sides)
    position_nodes_in_circle(self, other_nodes, pos_3d, center_z=0, radius=8, y_offset=8)

    return pos_3d


def add_impact_analysis_edges(self, fig, relationships, pos_3d):
    """Add edges for impact analysis with direction-based colors"""

    # Group edges by direction for different styling
    upstream_edges = []
    downstream_edges = []

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

            if rel['direction'] == 'incoming':
                upstream_edges.append(edge_data)
            else:
                downstream_edges.append(edge_data)

    # Add upstream edges (data sources)
    if upstream_edges:
        edge_x, edge_y, edge_z = [], [], []
        for edge in upstream_edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#00FF7F', width=4),  # Bright green for upstream
            opacity=0.8,
            name=f"⬅️ Upstream ({len(upstream_edges)})",
            showlegend=True,
            hoverinfo='none'
        ))

    # Add downstream edges (data consumers)
    if downstream_edges:
        edge_x, edge_y, edge_z = [], [], []
        for edge in downstream_edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#FF6347', width=4),  # Bright red for downstream
            opacity=0.8,
            name=f"➡️ Downstream ({len(downstream_edges)})",
            showlegend=True,
            hoverinfo='none'
        ))


def add_impact_analysis_nodes(self, fig, objects, pos_3d, target_iobj):
    """Add nodes for impact analysis with target highlighting"""

    # Group objects by whether they're the target or not
    target_objects = [obj for obj in objects if obj.get('is_target', False)]
    connected_objects = [obj for obj in objects if not obj.get('is_target', False)]

    # Add target InfoObject (highlighted)
    if target_objects:
        obj = target_objects[0]
        node_id = obj['node_id']

        if node_id in pos_3d:
            pos = pos_3d[node_id]

            fig.add_trace(go.Scatter3d(
                x=[pos['x']], y=[pos['y']], z=[pos['z']],
                mode='markers+text',
                marker=dict(
                    size=40,  # Larger size for target
                    color='#FFD700',  # Gold color for target
                    line=dict(width=4, color='white'),
                    opacity=1.0,
                    symbol='diamond'
                ),
                text=[f"🎯<br>{obj['name']}"],
                textposition="middle center",
                textfont=dict(size=12, color='white', family="Arial Black"),
                hovertemplate=f"<b>🎯 TARGET INFOOBJECT</b><br><b>{obj['name']}</b><br>Type: {obj['type_name']}<extra></extra>",
                name=f"🎯 Target: {target_iobj}",
                showlegend=True
            ))

    # Add connected objects by category
    categories = set(obj['category'] for obj in connected_objects)

    for category in categories:
        category_objects = [obj for obj in connected_objects if obj['category'] == category]

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
                info += f"Owner: {obj.get('owner', 'Unknown')}"
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


def prepare_impact_analysis_csv_with_sources(self, results):
    """Prepare CSV export for impact analysis with source information"""

    csv_data = []

    # Add header info with source information
    csv_data.append("InfoObject Impact Analysis Report with Source Connections")
    csv_data.append(f"Target InfoObject,{results['target_iobj']}")
    csv_data.append(f"Analysis Date,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    csv_data.append(f"Total Connected Objects,{results['total_objects']}")
    csv_data.append(f"Total Relationships,{results['total_relationships']}")
    csv_data.append(f"Total Source Connections,{results['total_source_connections']}")
    csv_data.append(f"Analysis Depth,{results['analysis_depth']}")
    csv_data.append("")

    # Source connections section
    if results['source_connections']:
        csv_data.append("Source Connections")
        csv_data.append("DataSource Name,Source System,Connection Type,Depth,Intermediate Object")

        for src_conn in results['source_connections']:
            intermediate = src_conn.get('intermediate_node', '').split(':')[-1] if src_conn.get('intermediate_node') else 'Direct'
            csv_data.append(f"{src_conn['source_name']},{src_conn.get('source_system', 'Unknown')}"
                            f",{src_conn['connection_type']},{src_conn['depth']},{intermediate}")

        csv_data.append("")

    # Connected objects section
    csv_data.append("Connected Objects")
    csv_data.append("Object Name,Object Type,Category,Owner,InfoArea,In Connections,Out Connections,Total Connections,Source System")

    for obj_type, objects in results['connected_objects'].items():
        for obj in objects:
            source_system = obj.get('source_system', '') if obj_type == 'DS' else ''
            csv_data.append(f"{obj['name']},{obj['type_name']},{obj['category']},{obj.get('owner', 'Unknown')},{obj.get('infoarea', 'UNASSIGNED')}"
                            f",{obj['connections_in']},{obj['connections_out']},{obj['total_connections']},{source_system}")

    csv_data.append("")

    # Relationships section
    csv_data.append("Relationships")
    csv_data.append("Source Object,Target Object,Connection Type,Direction,Depth")

    for rel in results['relationships']:
        source_name = rel['source'].split(':')[1] if ':' in rel['source'] else rel['source']
        target_name = rel['target'].split(':')[1] if ':' in rel['target'] else rel['target']
        csv_data.append(f"{source_name},{target_name},{rel['type']},{rel['direction']},{rel['depth']}")

    return '\n'.join(csv_data)


def generate_impact_analysis_report_with_sources(self, iobj_name, results):
    """Generate text report for impact analysis with source information"""

    report = f"""
═══════════════════════════════════════════════════════
    SAP BW INFOOBJECT IMPACT ANALYSIS WITH SOURCES
═══════════════════════════════════════════════════════

Target InfoObject: {iobj_name}
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Depth: {results['analysis_depth']} levels
Source Tracing: {'Enabled' if results.get('source_tracing_enabled', False) else 'Disabled'}

SUMMARY
-------
• Connected Objects: {results['total_objects']:,}
• Total Relationships: {results['total_relationships']:,}
• Source Connections: {results['total_source_connections']:,}

"""

    # Source system analysis
    if results['source_connections']:
        source_by_system = {}
        for src_conn in results['source_connections']:
            system = src_conn.get('source_system', 'Unknown')
            if system not in source_by_system:
                source_by_system[system] = []
            source_by_system[system].append(src_conn)

        report += "SOURCE SYSTEM ANALYSIS\n"
        report += "---------------------\n"
        for system, connections in source_by_system.items():
            unique_sources = set(conn['source_name'] for conn in connections)
            report += f"• {system}: {len(unique_sources)} DataSources, {len(connections)} connections\n"

            # List top DataSources for this system
            for src_name in sorted(unique_sources)[:5]:
                report += f"  - {src_name}\n"
            if len(unique_sources) > 5:
                report += f"  ... and {len(unique_sources) - 5} more DataSources\n"
        report += "\n"

    # Object type breakdown
    report += "IMPACT BREAKDOWN BY OBJECT TYPE\n"
    report += "-------------------------------\n"

    for obj_type, objects in results['connected_objects'].items():
        if objects:
            config = self.object_types[obj_type]
            report += f"\n{config['icon']} {config['name']}: {len(objects)} objects\n"

            # Enhanced display for DataSources
            if obj_type == 'DS':
                source_systems = set(obj.get('source_system', 'Unknown') for obj in objects)
                report += f"  Source Systems: {', '.join(sorted(source_systems))}\n"

            # List top 10 most connected objects
            sorted_objects = sorted(objects, key=lambda x: x.get('total_connections', 0), reverse=True)
            for obj in sorted_objects[:10]:
                connections_info = f"({obj.get('total_connections', 0)} connections)"
                if obj_type == 'DS' and 'source_system' in obj:
                    connections_info += f" - {obj['source_system']}"
                report += f"  • {obj['name']} {connections_info}\n"

            if len(objects) > 10:
                report += f"  ... and {len(objects) - 10} more objects\n"

    # Connection analysis
    upstream_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'incoming')
    downstream_count = sum(1 for rel in results['relationships'] if rel['direction'] == 'outgoing')

    report += f"""

CONNECTION ANALYSIS
------------------
• Upstream Dependencies: {upstream_count} (objects providing data TO {iobj_name})
• Downstream Impact: {downstream_count} (objects receiving data FROM {iobj_name})
• Source Connections: {results['total_source_connections']} (traced to DataSources)

SOURCE TRACEABILITY
------------------
"""

    if results['source_connections']:
        direct_sources = sum(1 for conn in results['source_connections'] if 'intermediate_node' not in conn)
        indirect_sources = results['total_source_connections'] - direct_sources

        report += f"• Direct Source Connections: {direct_sources}\n"
        report += f"• Indirect Source Connections: {indirect_sources}\n"
        report += f"• Source System Coverage: {len(set(conn.get('source_system', 'Unknown') for conn in results['source_connections']))} systems\n"
    else:
        report += "• No source connections found - InfoObject may be purely derived\n"

    report += """

IMPACT ASSESSMENT
-----------------
"""

    if downstream_count > upstream_count:
        report += f"• HIGH IMPACT: This InfoObject is widely used ({downstream_count} downstream connections)\n"
        report += "• Changes to this InfoObject could affect many downstream objects\n"
        report += "• Recommend careful testing before modifications\n"
    elif upstream_count > downstream_count:
        report += f"• MODERATE IMPACT: This InfoObject depends on {upstream_count} upstream sources\n"
        report += "• Changes to upstream objects could affect this InfoObject\n"
        report += "• Monitor upstream dependencies for changes\n"
    else:
        report += "• BALANCED: Equal upstream and downstream connections\n"
        report += "• Standard impact assessment recommended\n"

    # Source-specific recommendations
    if results['source_connections']:
        report += "\nSOURCE SYSTEM IMPACT:\n"
        source_systems = set(conn.get('source_system', 'Unknown') for conn in results['source_connections'])
        report += f"• This InfoObject depends on {len(source_systems)} source systems\n"
        report += f"• Source systems: {', '.join(sorted(source_systems))}\n"
        report += "• Consider impact of source system changes or outages\n"

    downstream_examples = [rel['target'].split(':')[1] for rel in results['relationships'][:5] if rel['direction'] == 'outgoing']
    upstream_examples = [rel['source'].split(':')[1] for rel in results['relationships'][:5] if rel['direction'] == 'incoming']
    source_examples = [conn['source_name'] for conn in results['source_connections'][:5]]

    report += f"""

RECOMMENDATIONS
--------------
• Document all connections before making changes
• Test with downstream objects: {', '.join(downstream_examples) if downstream_examples else 'None found'}
• Verify upstream data sources: {', '.join(upstream_examples) if upstream_examples else 'None found'}
• Monitor source systems: {', '.join(source_examples) if source_examples else 'None traced'}
• Consider impact on {results['total_objects']} connected objects
• Review source system dependencies for availability requirements

═══════════════════════════════════════════════════════
                END OF REPORT
═══════════════════════════════════════════════════════
"""

    return report
