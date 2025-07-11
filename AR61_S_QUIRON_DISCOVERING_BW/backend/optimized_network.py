import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import random
from collections import defaultdict
from connectors.source_detectors import get_source_system_info 


def get_connection_based_dataset(self, sample_type, selected_types, selected_infoareas,
                                 max_objects, min_connections, max_edges,
                                 highly_pct=0.4, well_pct=0.4, isolated_pct=0.2):
    """Get dataset based on connection patterns - NEW METHOD"""

    # Get all eligible objects with connection analysis
    all_objects = []

    for obj_type, objects in st.session_state.global_inventory.items():
        if obj_type in selected_types:
            for obj in objects:
                # Apply InfoArea filter
                if selected_infoareas and obj.get('infoarea', 'UNASSIGNED') not in selected_infoareas:
                    continue

                # Get connection count
                node_id = f"{obj_type}:{obj['name']}"
                connections = st.session_state.graph.degree(node_id) if node_id in st.session_state.graph.nodes else 0

                if connections >= min_connections:
                    obj_with_connections = obj.copy()
                    obj_with_connections['connections'] = connections
                    obj_with_connections['node_id'] = node_id
                    all_objects.append(obj_with_connections)

    # Calculate connection thresholds
    if all_objects:
        connection_counts = [obj['connections'] for obj in all_objects]
        avg_connections = sum(connection_counts) / len(connection_counts)

        # Categorize objects by connection level
        highly_connected = [obj for obj in all_objects if obj['connections'] > avg_connections * 2]
        well_connected = [obj for obj in all_objects if avg_connections <= obj['connections'] <= avg_connections * 2]
        isolated = [obj for obj in all_objects if obj['connections'] == 0]

        # Sample based on strategy
        sampled_objects = []

        if sample_type == "Show Highly Connected":
            sampled_objects = highly_connected[:max_objects]
        elif sample_type == "Show Well Connected":
            sampled_objects = well_connected[:max_objects]
        elif sample_type == "Show Isolated":
            sampled_objects = isolated[:max_objects]
        elif sample_type == "Show Mixed Distribution":
            # Mix according to specified percentages
            high_count = int(max_objects * highly_pct)
            well_count = int(max_objects * well_pct)
            isolated_count = int(max_objects * isolated_pct)

            sampled_objects.extend(highly_connected[:high_count])
            sampled_objects.extend(well_connected[:well_count])
            sampled_objects.extend(isolated[:isolated_count])

            # Fill remaining spots if needed
            remaining = max_objects - len(sampled_objects)
            if remaining > 0:
                remaining_objects = [obj for obj in all_objects if obj not in sampled_objects]
                sampled_objects.extend(remaining_objects[:remaining])

        # Get relevant relationships
        sampled_node_ids = set(obj['node_id'] for obj in sampled_objects)
        sampled_relationships = []

        for rel in st.session_state.relationships:
            if rel['source'] in sampled_node_ids and rel['target'] in sampled_node_ids:
                sampled_relationships.append(rel)
                if len(sampled_relationships) >= max_edges and max_edges > 0:
                    break

        return sampled_objects, sampled_relationships

    return [], []


def calculate_sampled_connection_stats(self, sampled_objects):
    """Calculate connection statistics for sampled objects - NEW METHOD"""

    if not sampled_objects:
        return {'connected_percentage': 0, 'avg_connections': 0}

    total_connections = sum(obj.get('connections', 0) for obj in sampled_objects)
    connected_count = sum(1 for obj in sampled_objects if obj.get('connections', 0) > 0)

    return {
        'connected_percentage': (connected_count / len(sampled_objects)) * 100,
        'avg_connections': total_connections / len(sampled_objects),
        'total_objects': len(sampled_objects),
        'connected_objects': connected_count,
        'isolated_objects': len(sampled_objects) - connected_count
    }


def create_connection_aware_3d_network(self, objects, relationships, render_quality,
                                       show_connection_percentages, line_intensity):
    """Create 3D network visualization with connection awareness - ENHANCED METHOD"""

    if not objects:
        return None

    # Calculate 3D positions for sampled objects
    sampled_graph = nx.DiGraph()

    # Add nodes
    for obj in objects:
        sampled_graph.add_node(obj['node_id'], **obj)

    # Add edges
    for rel in relationships:
        if rel['source'] in sampled_graph.nodes and rel['target'] in sampled_graph.nodes:
            sampled_graph.add_edge(rel['source'], rel['target'], **rel)

    # Calculate positions
    pos_3d = calculate_optimized_3d_positions(self, sampled_graph, render_quality)

    # Create visualization
    fig = go.Figure()

    # Add edges with connection-aware styling
    if relationships:
        add_connection_aware_3d_edges(self, fig, relationships, pos_3d, render_quality, line_intensity)

    # Add nodes by category with connection percentage display
    categories = set(obj['category'] for obj in objects)
    for category in categories:
        add_connection_aware_3d_nodes_by_category(
            self, fig, category, objects, pos_3d, render_quality, show_connection_percentages
        )

    # Update layout with enhanced connection info
    fig.update_layout(
        title={
            'text': f'🎯 Connection-Aware SAP BW 3D Network ({len(objects):,} objects, {len(relationships):,} connections)',
            'x': 0.5,
            'font': {'size': 20, 'color': 'white'}
        },
        scene=dict(
            xaxis=dict(
                title='X Dimension',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                showticklabels=False,
                backgroundcolor='black',
                color='white'
            ),
            yaxis=dict(
                title='Y Dimension',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                showticklabels=False,
                backgroundcolor='black',
                color='white'
            ),
            zaxis=dict(
                title='Z Layers (Sources → Providers)',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                backgroundcolor='black',
                color='white'
            ),
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
        legend=dict(
            bgcolor='rgba(0,0,0,0.8)',
            bordercolor='white',
            borderwidth=1,
            font=dict(color='white')
        ),
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig


def add_connection_aware_3d_edges(self, fig, relationships, pos_3d, render_quality, line_intensity):
    """Add connection-aware 3D edges with intensity-based styling - ENHANCED METHOD"""

    # Group edges by type with connection-aware styling
    edge_groups = {
        'transformation': {'color': '#00D4FF', 'width': 4, 'opacity': 0.8},
        'usage_dimension': {'color': '#FFB347', 'width': 2, 'opacity': 0.6},
        'usage_keyfigure': {'color': '#DA70D6', 'width': 2, 'opacity': 0.6},
        'source_connection': {'color': '#00FF7F', 'width': 3, 'opacity': 0.7},
        'default': {'color': '#90EE90', 'width': 2, 'opacity': 0.5}
    }

    # Adjust styling based on line intensity setting
    intensity_multipliers = {
        'Standard': 1.0,
        'Highlight Connected': 1.5,
        'Dim Isolated': 0.7
    }

    multiplier = intensity_multipliers.get(line_intensity, 1.0)

    # Update edge styling
    for edge_type, style in edge_groups.items():
        style['width'] = int(style['width'] * multiplier)
        style['opacity'] = min(1.0, style['opacity'] * multiplier)

    # Limit edge rendering based on performance mode
    if render_quality == "High Performance":
        max_edges_to_render = min(1000, len(relationships))
    elif render_quality == "Balanced":
        max_edges_to_render = min(3000, len(relationships))
    else:
        max_edges_to_render = min(5000, len(relationships))

    # Sort relationships by importance and connection strength
    sorted_relationships = sorted(relationships,
                                  key=lambda x: (0 if x['type'] == 'transformation' else
                                                 1 if x['type'] == 'usage_dimension' else
                                                 2 if x['type'] == 'usage_keyfigure' else
                                                 3 if x['type'] == 'source_connection' else 4))

    # Group edges by type for rendering
    edges_by_type = defaultdict(list)

    for rel in sorted_relationships[:max_edges_to_render]:
        source_id, target_id = rel['source'], rel['target']

        if source_id in pos_3d and target_id in pos_3d:
            pos0 = pos_3d[source_id]
            pos1 = pos_3d[target_id]

            edge_data = {
                'x0': pos0['x'], 'y0': pos0['y'], 'z0': pos0['z'],
                'x1': pos1['x'], 'y1': pos1['y'], 'z1': pos1['z'],
                'type': rel['type']
            }
            edges_by_type[rel['type']].append(edge_data)

    # Render edges by type with connection-aware colors and styles
    for edge_type, edges in edges_by_type.items():
        if not edges:
            continue

        edge_x, edge_y, edge_z = [], [], []

        for edge in edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        # Get enhanced style for this edge type
        style = edge_groups.get(edge_type, edge_groups['default'])

        # Create trace for this edge type
        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(
                color=style['color'],
                width=style['width']
            ),
            opacity=style['opacity'],
            hoverinfo='none',
            showlegend=True,
            name=f"{edge_type.replace('_', ' ').title()} ({len(edges)})",
            legendgroup='edges'
        ))


def add_connection_aware_3d_nodes_by_category(self, fig, category, objects, pos_3d, render_quality, show_connection_percentages):
    """Add 3D nodes with connection percentage awareness - ENHANCED METHOD"""
    category_objects = [obj for obj in objects if obj['category'] == category]

    if not category_objects:
        return

    node_x, node_y, node_z = [], [], []
    node_text, node_info, node_sizes = [], [], []

    # Calculate connection statistics for this category
    category_connections = [obj.get('connections', 0) for obj in category_objects]
    max_category_connections = max(category_connections) if category_connections else 1

    for obj in category_objects:
        node_id = obj['node_id']
        if node_id in pos_3d:
            pos = pos_3d[node_id]

            node_x.append(pos['x'])
            node_y.append(pos['y'])
            node_z.append(pos['z'])

            connections = obj.get('connections', 0)

            # Enhanced text with connection percentage if enabled
            if render_quality == "High Performance":
                node_text.append("")
            else:
                display_name = obj['name'][:8] + '...' if len(obj['name']) > 8 else obj['name']

                if show_connection_percentages and max_category_connections > 0:
                    connection_pct = (connections / max_category_connections) * 100
                    node_text.append(f"{obj['icon']}<br>{display_name}<br>({connection_pct:.0f}%)")
                else:
                    node_text.append(f"{obj['icon']}<br>{display_name}")

            # Enhanced hover info with connection analysis
            if render_quality == "High Quality":
                info = f"<b style='color: white;'>{obj['icon']} {obj['name']}</b><br>"
                info += f"<span style='color: #FFD700;'>Type:</span> {obj['type_name']}<br>"
                info += f"<span style='color: #FFD700;'>Category:</span> {obj['category']}<br>"
                info += f"<span style='color: #FFD700;'>Connections:</span> <b style='color: #00FF00;'>{connections}</b><br>"

                if max_category_connections > 0:
                    connection_pct = (connections / max_category_connections) * 100
                    info += f"<span style='color: #FFD700;'>Connection %:</span> <b style='color: #00FFFF;'>{connection_pct:.1f}%</b><br>"

                info += f"<span style='color: #FFD700;'>Owner:</span> {obj.get('owner', 'Unknown')}<br>"
                info += f"<span style='color: #FFD700;'>InfoArea:</span> {obj.get('infoarea', 'UNASSIGNED')}<br>"
                info += f"<span style='color: #FFD700;'>Status:</span> {obj.get('active', 'Unknown')}"

                # Add source system info for DataSources
                if obj.get('type') == 'DS':
                    info += f"<br><span style='color: #FFD700;'>Source System:</span> {get_source_system_info(self, obj['name'])}"
            else:
                info = f"<b>{obj['name']}</b><br>{obj['type_name']}<br>Connections: <b>{connections}</b>"
                if show_connection_percentages and max_category_connections > 0:
                    connection_pct = (connections / max_category_connections) * 100
                    info += f"<br>Connection %: <b>{connection_pct:.1f}%</b>"

            node_info.append(info)

            # Enhanced node size based on connections with better scaling
            base_size = obj['size_base'] * 0.9
            connection_bonus = min(connections * 3, 30)  # Increased scaling for connection awareness
            size = max(10, base_size + connection_bonus)
            node_sizes.append(size)

    if node_x:
        # Enhanced colors with connection-aware brightness
        base_color = category_objects[0]['color']

        # Make colors even brighter for connection awareness
        color_mapping = {
            '#FF6B6B': '#FF3333',  # Extra bright red for InfoCubes
            '#4ECDC4': '#00FFFF',  # Bright cyan for Advanced DSOs
            '#45B7D1': '#1E90FF',  # Bright blue for Classic DSOs
            '#96CEB4': '#00FF7F',  # Bright green for DataSources
            '#FFEAA7': '#FFD700',  # Gold for InfoObjects
            '#DDA0DD': '#DA70D6'   # Bright orchid for Transformations
        }

        display_color = color_mapping.get(base_color, base_color)

        fig.add_trace(go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers+text' if render_quality != "High Performance" else 'markers',
            marker=dict(
                size=node_sizes,
                color=display_color,
                line=dict(width=3, color='white'),  # Thicker outline for connection awareness
                opacity=0.95,  # Higher opacity for better visibility
                symbol=category_objects[0]['shape']
            ),
            text=node_text,
            textposition="middle center",
            textfont=dict(
                size=9,  # Slightly larger for connection percentages
                color='white',
                family="Arial Black"
            ),
            hovertemplate='%{hovertext}<extra></extra>',
            hovertext=node_info,
            name=f"{category} ({len(category_objects)})",
            showlegend=True,
            legendgroup='nodes'
        ))


def get_optimized_dataset(self, strategy, selected_types, selected_infoareas,
                          max_objects, min_connections, max_edges):
    """Get optimized dataset based on strategy"""

    # First, get all eligible objects
    eligible_objects = []

    for obj_type, objects in st.session_state.global_inventory.items():
        if obj_type in selected_types:
            for obj in objects:
                # Apply InfoArea filter
                if selected_infoareas and obj.get('infoarea', 'UNASSIGNED') not in selected_infoareas:
                    continue

                # Apply connection filter
                node_id = f"{obj_type}:{obj['name']}"
                connections = st.session_state.graph.degree(node_id) if node_id in st.session_state.graph.nodes else 0
                if connections < min_connections:
                    continue

                # Add connection count for sorting
                obj_with_connections = obj.copy()
                obj_with_connections['connections'] = connections
                obj_with_connections['node_id'] = node_id
                eligible_objects.append(obj_with_connections)

    # Apply sampling strategy
    if strategy == "🎯 Smart Sample (Recommended)":
        sampled_objects = smart_sample(self, eligible_objects, max_objects)
    elif strategy == "🔍 Filtered View":
        sampled_objects = eligible_objects[:max_objects]
    elif strategy == "📊 Category Focus":
        sampled_objects = category_balanced_sample(self, eligible_objects, max_objects)
    elif strategy == "🎲 Random Sample":
        sampled_objects = random.sample(eligible_objects, min(max_objects, len(eligible_objects)))
    elif strategy == "🔗 Most Connected Only":
        eligible_objects.sort(key=lambda x: x['connections'], reverse=True)
        sampled_objects = eligible_objects[:max_objects]
    else:
        sampled_objects = eligible_objects[:max_objects]

    # Get relevant relationships
    sampled_node_ids = set(obj['node_id'] for obj in sampled_objects)
    sampled_relationships = []

    for rel in st.session_state.relationships:
        if rel['source'] in sampled_node_ids and rel['target'] in sampled_node_ids:
            sampled_relationships.append(rel)
            if len(sampled_relationships) >= max_edges and max_edges > 0:
                break

    return sampled_objects, sampled_relationships


def smart_sample(self, objects, max_objects):
    """Smart sampling prioritizing important objects"""
    if len(objects) <= max_objects:
        return objects

    # Separate by priority
    high_priority = [obj for obj in objects if self.object_types[obj['type']]['priority'] == 3]
    medium_priority = [obj for obj in objects if self.object_types[obj['type']]['priority'] == 2]
    low_priority = [obj for obj in objects if self.object_types[obj['type']]['priority'] == 1]

    # Sort each priority group by connections
    high_priority.sort(key=lambda x: x['connections'], reverse=True)
    medium_priority.sort(key=lambda x: x['connections'], reverse=True)
    low_priority.sort(key=lambda x: x['connections'], reverse=True)

    # Allocate samples
    sampled = []

    # Take top connected from high priority (60% of sample)
    high_count = min(len(high_priority), int(max_objects * 0.6))
    sampled.extend(high_priority[:high_count])

    # Take top connected from medium priority (30% of sample)
    medium_count = min(len(medium_priority), int(max_objects * 0.3))
    sampled.extend(medium_priority[:medium_count])

    # Fill remaining with low priority
    remaining = max_objects - len(sampled)
    if remaining > 0:
        low_count = min(len(low_priority), remaining)
        sampled.extend(low_priority[:low_count])

    return sampled[:max_objects]


def category_balanced_sample(self, objects, max_objects):
    """Sample maintaining balance across categories"""
    if len(objects) <= max_objects:
        return objects

    # Group by category
    by_category = defaultdict(list)
    for obj in objects:
        by_category[obj['category']].append(obj)

    # Calculate objects per category
    categories = list(by_category.keys())
    objects_per_category = max_objects // len(categories)
    remaining = max_objects % len(categories)

    sampled = []
    for i, category in enumerate(categories):
        category_objects = by_category[category]
        # Sort by connections
        category_objects.sort(key=lambda x: x['connections'], reverse=True)

        # Take objects for this category
        take_count = objects_per_category
        if i < remaining:  # Distribute remaining objects
            take_count += 1

        sampled.extend(category_objects[:min(take_count, len(category_objects))])

    return sampled


def create_optimized_3d_network(self, objects, relationships, render_quality):
    """Create optimized 3D network visualization with black background"""

    if not objects:
        return None

    # Calculate 3D positions for sampled objects
    sampled_graph = nx.DiGraph()

    # Add nodes
    for obj in objects:
        sampled_graph.add_node(obj['node_id'], **obj)

    # Add edges
    for rel in relationships:
        if rel['source'] in sampled_graph.nodes and rel['target'] in sampled_graph.nodes:
            sampled_graph.add_edge(rel['source'], rel['target'], **rel)

    # Calculate positions
    pos_3d = calculate_optimized_3d_positions(self, sampled_graph, render_quality)

    # Create visualization
    fig = go.Figure()

    # Always add edges to show connections (improved visibility)
    if relationships:
        add_optimized_3d_edges(self, fig, relationships, pos_3d, render_quality)

    # Add nodes by category
    categories = set(obj['category'] for obj in objects)
    for category in categories:
        add_optimized_3d_nodes_by_category(self, fig, category, objects, pos_3d, render_quality)

    # Update layout with black background and improved visibility
    fig.update_layout(
        title={
            'text': f'🎯 SAP BW 3D Network ({len(objects):,} objects, {len(relationships):,} connections)',
            'x': 0.5,
            'font': {'size': 20, 'color': 'white'}
        },
        scene=dict(
            xaxis=dict(
                title='X Dimension',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                showticklabels=False,
                backgroundcolor='black',
                color='white'
            ),
            yaxis=dict(
                title='Y Dimension',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                showticklabels=False,
                backgroundcolor='black',
                color='white'
            ),
            zaxis=dict(
                title='Z Layers (Sources → Providers)',
                showgrid=True,
                gridcolor='rgba(100,100,100,0.3)',
                backgroundcolor='black',
                color='white'
            ),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            bgcolor='black',  # Black background
            aspectmode='cube'
        ),
        paper_bgcolor='black',  # Overall background
        plot_bgcolor='black',   # Plot area background
        font=dict(color='white'),  # All text white
        width=1200,
        height=800,
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0,0,0,0.8)',
            bordercolor='white',
            borderwidth=1,
            font=dict(color='white')
        ),
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig


def calculate_optimized_3d_positions(self, graph, render_quality):
    """Calculate optimized 3D positions"""
    if not graph.nodes:
        return {}

    # Choose layout algorithm based on size and quality
    node_count = len(graph.nodes)

    if render_quality == "High Performance" or node_count > 2000:
        # Fast circular layout for large graphs
        pos_2d = nx.circular_layout(graph)
    elif render_quality == "Balanced" or node_count > 1000:
        # Spring layout with fewer iterations
        pos_2d = nx.spring_layout(graph, k=2, iterations=20, seed=42)
    else:
        # High quality spring layout
        pos_2d = nx.spring_layout(graph, k=3, iterations=100, seed=42)

    pos_3d = {}
    for node_id in graph.nodes():
        node = graph.nodes[node_id]
        x, y = pos_2d[node_id]

        # Z position based on layer and connections
        base_z = node['z_layer'] * 2
        connections = graph.degree(node_id)
        z_variation = (connections / 50) * 0.5  # Reduced variation for performance

        pos_3d[node_id] = {
            'x': x * 8,  # Slightly smaller scale for performance
            'y': y * 8,
            'z': base_z + z_variation,
            'connections': connections
        }

    return pos_3d


def add_optimized_3d_edges(self, fig, relationships, pos_3d, render_quality):
    """Add optimized 3D edges with enhanced visibility on black background"""

    # Group edges by type for different styling and better visibility
    edge_groups = {
        'transformation': {'color': '#00D4FF', 'width': 4, 'opacity': 0.8},  # Bright cyan
        'usage_dimension': {'color': '#FFB347', 'width': 2, 'opacity': 0.6},  # Bright orange
        'usage_keyfigure': {'color': '#DA70D6', 'width': 2, 'opacity': 0.6},  # Bright orchid
        'source_connection': {'color': '#00FF7F', 'width': 3, 'opacity': 0.7},  # Bright green
        'default': {'color': '#90EE90', 'width': 2, 'opacity': 0.5}  # Light green
    }

    # Limit edge rendering based on performance mode
    if render_quality == "High Performance":
        max_edges_to_render = min(1000, len(relationships))
    elif render_quality == "Balanced":
        max_edges_to_render = min(3000, len(relationships))
    else:
        max_edges_to_render = min(5000, len(relationships))

    # Sort relationships by importance (transformations first, then by type)
    sorted_relationships = sorted(relationships,
                                  key=lambda x: (0 if x['type'] == 'transformation' else
                                                 1 if x['type'] == 'usage_dimension' else
                                                 2 if x['type'] == 'usage_keyfigure' else
                                                 3 if x['type'] == 'source_connection' else 4))

    # Group edges by type for rendering
    edges_by_type = defaultdict(list)

    for rel in sorted_relationships[:max_edges_to_render]:
        source_id, target_id = rel['source'], rel['target']

        if source_id in pos_3d and target_id in pos_3d:
            pos0 = pos_3d[source_id]
            pos1 = pos_3d[target_id]

            edge_data = {
                'x0': pos0['x'], 'y0': pos0['y'], 'z0': pos0['z'],
                'x1': pos1['x'], 'y1': pos1['y'], 'z1': pos1['z'],
                'type': rel['type']
            }
            edges_by_type[rel['type']].append(edge_data)

    # Render edges by type with different colors and styles
    for edge_type, edges in edges_by_type.items():
        if not edges:
            continue

        edge_x, edge_y, edge_z = [], [], []

        for edge in edges:
            edge_x.extend([edge['x0'], edge['x1'], None])
            edge_y.extend([edge['y0'], edge['y1'], None])
            edge_z.extend([edge['z0'], edge['z1'], None])

        # Get style for this edge type
        style = edge_groups.get(edge_type, edge_groups['default'])

        # Create trace for this edge type
        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(
                color=style['color'],
                width=style['width']
            ),
            opacity=style['opacity'],
            hoverinfo='none',
            showlegend=True,
            name=f"{edge_type.replace('_', ' ').title()} ({len(edges)})",
            legendgroup='edges'
        ))

    # Add a summary trace if we have edges
    if edges_by_type:
        total_edges_shown = sum(len(edges) for edges in edges_by_type.values())

        # Add invisible trace for legend organization
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='lines',
            line=dict(color='white', width=1),
            name=f"── Connections ({total_edges_shown:,}) ──",
            showlegend=True,
            legendgroup='edges'
        ))


def add_optimized_3d_nodes_by_category(self, fig, category, objects, pos_3d, render_quality):
    """Add optimized 3D nodes for a category with black background compatibility"""
    category_objects = [obj for obj in objects if obj['category'] == category]

    if not category_objects:
        return

    node_x, node_y, node_z = [], [], []
    node_text, node_info, node_sizes = [], [], []

    for obj in category_objects:
        node_id = obj['node_id']
        if node_id in pos_3d:
            pos = pos_3d[node_id]

            node_x.append(pos['x'])
            node_y.append(pos['y'])
            node_z.append(pos['z'])

            # Enhanced text visibility for black background
            if render_quality == "High Performance":
                node_text.append("")  # No text for performance
            else:
                display_name = obj['name'][:10] + '...' if len(obj['name']) > 10 else obj['name']
                node_text.append(f"{obj['icon']}<br>{display_name}")

            # Enhanced hover info with better formatting
            connections = obj['connections']
            if render_quality == "High Quality":
                info = f"<b style='color: white;'>{obj['icon']} {obj['name']}</b><br>"
                info += f"<span style='color: #FFD700;'>Type:</span> {obj['type_name']}<br>"
                info += f"<span style='color: #FFD700;'>Category:</span> {obj['category']}<br>"
                info += f"<span style='color: #FFD700;'>Owner:</span> {obj.get('owner', 'Unknown')}<br>"
                info += f"<span style='color: #FFD700;'>InfoArea:</span> {obj.get('infoarea', 'UNASSIGNED')}<br>"
                info += f"<span style='color: #FFD700;'>Connections:</span> <b style='color: #00FF00;'>{connections}</b><br>"
                info += f"<span style='color: #FFD700;'>Status:</span> {obj.get('active', 'Unknown')}"
            else:
                info = f"<b>{obj['name']}</b><br>{obj['type_name']}<br>Connections: <b>{connections}</b>"

            node_info.append(info)

            # Enhanced node size with better visibility
            base_size = obj['size_base'] * 0.9
            connection_bonus = min(connections * 2, 25)  # Cap the connection bonus
            size = max(8, base_size + connection_bonus)
            node_sizes.append(size)

    if node_x:
        # Enhanced colors and visibility for black background
        base_color = category_objects[0]['color']

        # Make colors brighter for black background
        color_mapping = {
            '#FF6B6B': '#FF4444',  # Brighter red for InfoCubes
            '#4ECDC4': '#00FFFF',  # Bright cyan for Advanced DSOs
            '#45B7D1': '#1E90FF',  # Bright blue for Classic DSOs
            '#96CEB4': '#00FF7F',  # Bright green for DataSources
            '#FFEAA7': '#FFD700',  # Gold for InfoObjects
            '#DDA0DD': '#DA70D6'   # Bright orchid for Transformations
        }

        display_color = color_mapping.get(base_color, base_color)

        fig.add_trace(go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers+text' if render_quality != "High Performance" else 'markers',
            marker=dict(
                size=node_sizes,
                color=display_color,
                line=dict(width=2, color='white'),  # White outline for contrast
                opacity=0.9,  # Higher opacity for better visibility
                symbol=category_objects[0]['shape']  # Use the proper shape
            ),
            text=node_text,
            textposition="middle center",
            textfont=dict(
                size=8,
                color='white',  # White text
                family="Arial Black"  # Bold font for better visibility
            ),
            hovertemplate='%{hovertext}<extra></extra>',
            hovertext=node_info,
            name=f"{category} ({len(category_objects)})",
            showlegend=True,
            legendgroup='nodes'
        ))
