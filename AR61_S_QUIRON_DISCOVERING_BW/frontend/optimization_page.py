import streamlit as st
import plotly.express as px
from backend.infocube_analysis import calculate_connection_percentages
from backend.optimized_network import get_connection_based_dataset
from backend.optimized_network import get_optimized_dataset
from backend.optimized_network import calculate_sampled_connection_stats
from backend.optimized_network import create_connection_aware_3d_network
from backend.impact_analysis import analyze_infoobject_impact_with_sources, create_impact_analysis_3d_visualization


def show_optimized_3d_visualization_page(self):
    """Show optimized 3D network visualization with connection percentage analysis"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("🎯 Advanced 3D Network Visualization with Connection Analysis")

    total_objects = sum(len(objects) for objects in st.session_state.global_inventory.values())
    connection_stats = calculate_connection_percentages(self)

    # Performance warning and connection overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Objects", f"{total_objects:,}")
    with col2:
        st.metric("Connected %", f"{connection_stats['overall_connected_percentage']:.1f}%")
    with col3:
        st.metric("Avg Connections", f"{connection_stats['average_connections']:.1f}")
    with col4:
        st.metric("Max Connections", f"{connection_stats['max_connections']}")

    if total_objects > 10000:
        st.warning(f"⚠️ Large dataset ({total_objects:,}objects). Using smart sampling and performance optimizations with connection-based filtering")

    # Enhanced visualization strategy selection
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🎨 Visualization Strategy")

        viz_strategy = st.selectbox(
            "Choose visualization approach:",
            [
                "🎯 Smart Sample (Recommended)",
                "🔗 Connection-Based Sampling",  # NEW OPTION
                "🔍 Filtered View",
                "📊 Category Focus",
                "🎲 Random Sample",
                "🔗 Most Connected Only",
                "🏷️ InfoObject Impact Focus"
            ],
            help="Different strategies for handling large datasets with connection analysis"
        )

        # Enhanced connection-based options
        if viz_strategy == "🔗 Connection-Based Sampling":
            connection_sample_type = st.selectbox(
                "Connection Sampling Strategy:",
                ["Show Highly Connected", "Show Well Connected", "Show Isolated", "Show Mixed Distribution"],
                help="Focus on objects with specific connection patterns"
            )

            if connection_sample_type == "Show Mixed Distribution":
                # Allow custom distribution
                highly_connected_pct = st.slider("% Highly Connected", 0, 100, 40)
                well_connected_pct = st.slider("% Well Connected", 0, 100, 40)
                isolated_pct = st.slider("% Isolated", 0, 100, 20)

                # Normalize percentages
                total_pct = highly_connected_pct + well_connected_pct + isolated_pct
                if total_pct > 0:
                    highly_connected_pct = highly_connected_pct / total_pct
                    well_connected_pct = well_connected_pct / total_pct
                    isolated_pct = isolated_pct / total_pct

        # InfoObject selection for impact focus
        if viz_strategy == "🏷️ InfoObject Impact Focus":
            iobj_list = []
            if 'IOBJ' in st.session_state.global_inventory:
                iobj_list = [obj['name'] for obj in st.session_state.global_inventory['IOBJ']]
                iobj_list.sort()

            if iobj_list:
                selected_iobj_for_viz = st.selectbox(
                    "Select InfoObject:",
                    options=iobj_list,
                    help="Show connections for this specific InfoObject"
                )
            else:
                st.error("No InfoObjects found")
                viz_strategy = "🎯 Smart Sample (Recommended)"

        # Object count control with connection awareness
        max_objects = st.slider(
            "Max objects to display:",
            min_value=100,
            max_value=min(5000, total_objects),
            value=min(1000, total_objects),
            step=100,
            help="Reduce for better performance. Connection filtering applied automatically."
        )

    with col2:
        st.subheader("🔍 Enhanced Filters with Connection Analysis")

        # Object type filters with connection stats
        priority_types = [k for k, v in self.object_types.items() if v['priority'] >= 2]
        selected_types = st.multiselect(
            "Select Object Types:",
            options=list(self.object_types.keys()),
            default=priority_types,
            format_func=lambda x: (f"{self.object_types[x]['icon']} {self.object_types[x]['name']}"
                                   f"({connection_stats['by_object_type'].get(x, {}).get('connected_percentage', 0):.1f}% connected)")
        )

        # Connection-based filtering
        st.markdown("**🔗 Connection Filtering**")
        connection_filter_enabled = st.checkbox("Enable Connection Filtering", value=True)

        if connection_filter_enabled:
            connection_threshold = st.selectbox(
                "Connection Threshold:",
                ["Show All", "Connected Only (>0)", "Well Connected (>avg)", "Highly Connected (>2×avg)", "Custom"],
                help="Filter objects based on connection count"
            )

            if connection_threshold == "Custom":
                min_connections_viz = st.number_input("Minimum connections:", min_value=0, value=0)
            else:
                if connection_threshold == "Connected Only (>0)":
                    min_connections_viz = 1
                elif connection_threshold == "Well Connected (>avg)":
                    min_connections_viz = int(connection_stats['average_connections'])
                elif connection_threshold == "Highly Connected (>2×avg)":
                    min_connections_viz = int(connection_stats['average_connections'] * 2)
                else:
                    min_connections_viz = 0
        else:
            min_connections_viz = 0

        # InfoArea filter for focused analysis
        all_infoareas = set()
        for objects in st.session_state.global_inventory.values():
            for obj in objects:
                all_infoareas.add(obj.get('infoarea', 'UNASSIGNED'))

        selected_infoareas = st.multiselect(
            "Focus on InfoAreas:",
            options=sorted(all_infoareas),
            default=[],
            help="Limit to specific business areas"
        )

    with col3:
        st.subheader("⚡ Performance & Connection Display")

        # Rendering quality
        render_quality = st.selectbox(
            "Rendering Quality:",
            ["High Performance", "Balanced", "High Quality"],
            index=0 if total_objects > 10000 else 1
        )

        # Enhanced connection display options
        st.markdown("**🔗 Connection Visualization**")
        show_connection_percentages = st.checkbox(
            "Show Connection Percentages",
            value=True,
            help="Display connection percentages in node labels"
        )

        connection_line_intensity = st.selectbox(
            "Connection Line Intensity:",
            ["Standard", "Highlight Connected", "Dim Isolated"],
            help="Adjust visual emphasis based on connections"
        )

        # Edge limit control with connection awareness
        max_edges = st.slider(
            "Max connections to display:",
            min_value=500,
            max_value=min(10000, len(st.session_state.relationships)),
            value=min(2000, len(st.session_state.relationships)),
            step=250,
            help="Reduce for better performance. Prioritizes high-value connections."
        )

        # Physics simulation
        enable_physics = st.checkbox("Enable physics simulation", value=False)

        # Connection statistics display
        st.markdown("**📊 Quick Connection Stats**")
        if selected_types:
            for obj_type in selected_types[:3]:  # Show top 3 selected types
                type_stats = connection_stats['by_object_type'].get(obj_type, {})
                if type_stats:
                    st.write(f"• {self.object_types[obj_type]['icon']} {type_stats.get('connected_percentage', 0):.1f}% connected")

    st.markdown("---")

    # Enhanced generate visualization button
    if st.button("🎨 Generate 3D Visualization with Connection Analysis", type="primary"):
        with st.spinner("🎯 Creating connection-aware 3D visualization..."):

            # Get optimized dataset with connection analysis
            if viz_strategy == "🔗 Connection-Based Sampling":
                sampled_objects, sampled_relationships = get_connection_based_dataset(
                    self,
                    connection_sample_type, selected_types, selected_infoareas,
                    max_objects, min_connections_viz, max_edges,
                    locals().get('highly_connected_pct', 0.4),
                    locals().get('well_connected_pct', 0.4),
                    locals().get('isolated_pct', 0.2)
                )
            elif viz_strategy == "🏷️ InfoObject Impact Focus":
                # Use InfoObject impact analysis for visualization
                impact_results = analyze_infoobject_impact_with_sources(
                    self, selected_iobj_for_viz, 2, True, ['transformation', 'usage_dimension', 'usage_keyfigure'], True
                )

                if impact_results:
                    sampled_objects = []

                    # Add target InfoObject
                    for obj in st.session_state.global_inventory.get('IOBJ', []):
                        if obj['name'] == selected_iobj_for_viz:
                            target_obj = obj.copy()
                            target_obj['node_id'] = f"IOBJ:{selected_iobj_for_viz}"
                            target_obj['connections'] = len(impact_results['relationships'])
                            target_obj['is_target'] = True
                            sampled_objects.append(target_obj)
                            break

                    # Add connected objects
                    for obj_type, objects in impact_results['connected_objects'].items():
                        for obj in objects:
                            obj_enhanced = obj.copy()
                            obj_enhanced['connections'] = obj.get('total_connections', 0)
                            obj_enhanced['is_target'] = False
                            sampled_objects.append(obj_enhanced)

                    sampled_relationships = impact_results['relationships']
                else:
                    st.error(f"No connections found for InfoObject: {selected_iobj_for_viz}")
                    return
            else:
                # Standard sampling methods with connection filtering
                sampled_objects, sampled_relationships = get_optimized_dataset(
                    self,
                    viz_strategy, selected_types, selected_infoareas,
                    max_objects, min_connections_viz, max_edges
                )

            if not sampled_objects:
                st.error("No objects match the selected criteria")
                return

            # Calculate connection percentages for sampled objects
            sampled_connection_stats = calculate_sampled_connection_stats(self, sampled_objects)

            # Show what we're visualizing with connection analysis
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"📊 Visualizing {len(sampled_objects):,} objects")
            with col2:
                st.info(f"🔗 {len(sampled_relationships):,} relationships")
            with col3:
                st.info(f"📈 {sampled_connection_stats['connected_percentage']:.1f}% connected")

            # Create enhanced 3D visualization with connection analysis
            if viz_strategy == "🏷️ InfoObject Impact Focus":
                # Use specialized impact analysis visualization
                fig = create_impact_analysis_3d_visualization(self,
                                                              sampled_objects, sampled_relationships, selected_iobj_for_viz)
            else:
                # Use enhanced standard visualization with connection analysis
                fig = create_connection_aware_3d_network(
                    self, sampled_objects, sampled_relationships, render_quality,
                    True, enable_physics, show_connection_percentages, connection_line_intensity
                )

            if fig:
                st.plotly_chart(fig, use_container_width=True, height=800)

                # Enhanced success message with connection insights
                st.success("✅ Connection-aware visualization rendered successfully!")

                # Show detailed sampling info with connection analysis
                with st.expander("📊 Visualization Details with Connection Analysis"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Objects Displayed", len(sampled_objects))
                        st.metric("Total Available", total_objects)
                    with col2:
                        st.metric("Relationships Shown", len(sampled_relationships))
                        st.metric("Total Available", len(st.session_state.relationships))
                    with col3:
                        coverage = (len(sampled_objects) / total_objects) * 100
                        st.metric("Dataset Coverage", f"{coverage:.1f}%")
                        st.metric("Connected Objects", f"{sampled_connection_stats['connected_percentage']:.1f}%")
                    with col4:
                        st.metric("Avg Connections", f"{sampled_connection_stats['avg_connections']:.1f}")
                        if viz_strategy == "🏷️ InfoObject Impact Focus":
                            st.metric("Focus InfoObject", selected_iobj_for_viz)

                    # Connection distribution in sample
                    if len(sampled_objects) > 1:
                        connection_counts = [obj.get('connections', 0) for obj in sampled_objects]
                        fig_dist = px.histogram(
                            x=connection_counts,
                            nbins=20,
                            title="Connection Distribution in Visualization",
                            labels={'x': 'Connections', 'y': 'Count'}
                        )
                        fig_dist.update_layout(height=250)
                        st.plotly_chart(fig_dist, use_container_width=True)

                # Enhanced navigation tips with connection analysis info
                if viz_strategy == "🏷️ InfoObject Impact Focus":
                    st.info(f"""
                    🎮 **InfoObject Impact Analysis Navigation:**
                    - **🎯 Gold Diamond** = Target InfoObject ({selected_iobj_for_viz})
                    - **⬅️ Green Lines** = Upstream dependencies (data sources)
                    - **➡️ Red Lines** = Downstream impact (data consumers)
                    - **Node sizes** reflect total connections
                    - **Connection percentages** shown in labels
                    - **Hover** for detailed impact and connection information
                    """)
                else:
                    connection_tip = ""
                    if show_connection_percentages:
                        connection_tip = "\n        - **Connection %** displayed in node labels"

                    st.info(f"""
                    🎮 **3D Connection-Aware Navigation:**
                    - **Drag** to rotate the 3D space
                    - **Scroll** to zoom in/out
                    - **Hover** over nodes for connection details
                    - **Click legend** items to toggle object types
                    - **Double-click** to reset view{connection_tip}

                    🎨 **Connection-Based Visual Features:**
                    - **Node sizes** reflect connection importance
                    - **Bright connection lines** show relationships:
                        • 🔵 Cyan = Transformations (data flow)
                        • 🟠 Orange = Dimension usage
                        • 🟣 Purple = Key figure usage
                        • 🟢 Green = Source connections
                    - **{connection_line_intensity}** line intensity for connection emphasis
                    - **Black background** for optimal visibility
                    """)
            else:
                st.error("Failed to generate visualization")
