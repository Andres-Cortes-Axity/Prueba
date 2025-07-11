import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from backend.infocube_analysis import calculate_connection_percentages
from backend.reports import generate_search_connection_summary
from connectors.source_detectors import get_source_system_info
from connectors.source_detectors import determine_infosource_type


def show_object_explorer(self):
    """Show object explorer with connection percentage analysis and filtering"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("🔍 Enhanced Object Explorer with Connection Analysis")

    # Performance note and connection statistics
    total_objects = st.session_state.dataset_stats['total_objects']
    connection_stats = calculate_connection_percentages(self)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Objects", f"{total_objects:,}")
    with col2:
        st.metric("Connected Objects", f"{connection_stats['overall_connected_percentage']:.1f}%")
    with col3:
        st.metric("Isolated Objects", f"{connection_stats['isolated_percentage']:.1f}%")
    with col4:
        st.metric("Avg Connections", f"{connection_stats['average_connections']:.1f}")

    if total_objects > 20000:
        st.info(f"📊 Large dataset ({total_objects:,} objects) - Using optimized search with connection analysis")

    # Enhanced search and filter controls
    col1, col2, col3 = st.columns(3)

    with col1:
        search_term = st.text_input("🔍 Search objects:", placeholder="Enter object name...")

    with col2:
        object_type_filter = st.selectbox(
            "Filter by type:",
            options=["All"] + list(self.object_types.keys()),
            format_func=lambda x: f"{self.object_types[x]['icon']} {self.object_types[x]['name']}" if x != "All" else "All Types"
        )

    with col3:
        category_filter = st.selectbox(
            "Filter by category:",
            options=["All", "Provider", "Source", "Metadata", "Process"]
        )

    # Enhanced connection filtering options
    st.markdown("### 🔗 Connection-Based Filtering")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Connection Range Filter**")
        connection_filter_type = st.selectbox(
            "Connection Filter Type:",
            options=["All Objects", "Connected Only", "Isolated Only", "Highly Connected", "Custom Range"],
            help="Filter objects based on their connection patterns"
        )

        if connection_filter_type == "Custom Range":
            min_connections = st.number_input("Min connections:", min_value=0, value=0)
            max_connections = st.number_input("Max connections:", min_value=0, value=1000)
        else:
            min_connections = 0
            max_connections = 1000

            if connection_filter_type == "Connected Only":
                min_connections = 1
            elif connection_filter_type == "Isolated Only":
                max_connections = 0
            elif connection_filter_type == "Highly Connected":
                min_connections = int(connection_stats['average_connections'] * 2)

    with col2:
        st.markdown("**Connection Percentage Analysis**")

        # Show connection percentages by type
        if object_type_filter != "All":
            type_stats = connection_stats['by_object_type'].get(object_type_filter, {})
            if type_stats:
                st.metric("Type Connection Rate", f"{type_stats.get('connected_percentage', 0):.1f}%")
                st.metric("Type Avg Connections", f"{type_stats.get('average_connections', 0):.1f}")

        show_connection_percentage = st.checkbox(
            "Show Connection Percentages",
            value=True,
            help="Display connection percentages in results"
        )

    with col3:
        st.markdown("**Advanced Filters**")
        # InfoArea filter
        all_infoareas = set()
        for objects in st.session_state.global_inventory.values():
            for obj in objects:
                all_infoareas.add(obj.get('infoarea', 'UNASSIGNED'))

        infoarea_filter = st.multiselect(
            "Filter by InfoArea:",
            options=sorted(all_infoareas),
            default=[]
        )

        # Owner filter
        owner_filter = st.text_input("Filter by owner:", placeholder="Owner name...")

    # Results limit
    max_results = st.slider("Max results to display:", 100, 5000, 1000, 100)

    # Enhanced search button
    if st.button("🔍 Search Objects with Connection Analysis", type="primary"):
        with st.spinner("Searching objects with connection analysis..."):

            filtered_objects = []
            result_count = 0

            for obj_type, objects in st.session_state.global_inventory.items():
                # Apply type filter
                if object_type_filter != "All" and obj_type != object_type_filter:
                    continue

                for obj in objects:
                    # Apply category filter
                    if category_filter != "All" and obj['category'] != category_filter:
                        continue

                    # Apply search filter
                    if search_term and search_term.lower() not in obj['name'].lower():
                        continue

                    # Apply InfoArea filter
                    if infoarea_filter and obj.get('infoarea', 'UNASSIGNED') not in infoarea_filter:
                        continue

                    # Apply owner filter
                    if owner_filter and owner_filter.lower() not in obj.get('owner', '').lower():
                        continue

                    # Get connection count and calculate percentage
                    node_id = f"{obj_type}:{obj['name']}"
                    connections = st.session_state.graph.degree(node_id) if node_id in st.session_state.graph.nodes else 0

                    # Apply connection range filter
                    if connections < min_connections or connections > max_connections:
                        continue

                    # Calculate connection percentage within type
                    type_stats = connection_stats['by_object_type'].get(obj_type, {})
                    type_max_connections = 0
                    if type_stats and type_stats.get('total', 0) > 0:
                        # Find max connections for this type
                        for check_obj in objects:
                            check_node_id = f"{obj_type}:{check_obj['name']}"
                            check_connections = st.session_state.graph.degree(check_node_id) if check_node_id in st.session_state.graph.nodes else 0
                            type_max_connections = max(type_max_connections, check_connections)

                    connection_percentage = (connections / type_max_connections * 100) if type_max_connections > 0 else 0

                    # Add enhanced information for all objects
                    enhanced_obj = {
                        'Icon': obj['icon'],
                        'Name': obj['name'],
                        'Type': obj['type_name'],
                        'Category': obj['category'],
                        'Owner': obj.get('owner', 'Unknown'),
                        'InfoArea': obj.get('infoarea', 'UNASSIGNED'),
                        'Active': obj.get('active', 'Unknown'),
                        'Connections': connections,
                        'Connection Status': 'Connected' if connections > 0 else 'Isolated',
                        'Last Changed': obj.get('last_changed', 'Unknown')
                    }

                    # Add connection percentage if requested
                    if show_connection_percentage:
                        enhanced_obj['Connection %'] = f"{connection_percentage:.1f}%"

                    # Add source system info for DataSources
                    if obj_type == 'DS':
                        enhanced_obj['Source System'] = get_source_system_info(self, obj['name'])
                        enhanced_obj['InfoSource Type'] = determine_infosource_type(self, obj['name'])

                    filtered_objects.append(enhanced_obj)

                    result_count += 1
                    if result_count >= max_results:
                        break

                if result_count >= max_results:
                    break

            if filtered_objects:
                st.success(f"✅ Found {len(filtered_objects):,} objects with connection analysis")

                # Convert to dataframe and display
                df = pd.DataFrame(filtered_objects)

                # Enhanced sorting options
                col1, col2, col3 = st.columns(3)
                with col1:
                    sort_by = st.selectbox(
                        "Sort by:",
                        options=['Connections', 'Name', 'Type', 'Owner', 'InfoArea', 'Connection Status'] + (['Connection %']
                                                                                                             if show_connection_percentage else []),
                        index=0
                    )
                with col2:
                    sort_order = st.selectbox("Order:", options=['Descending', 'Ascending'])
                with col3:
                    # Quick filter buttons
                    if st.button("Show Only Connected"):
                        df = df[df['Connection Status'] == 'Connected']
                    elif st.button("Show Only Isolated"):
                        df = df[df['Connection Status'] == 'Isolated']

                # Apply sorting
                ascending = sort_order == 'Ascending'
                if sort_by == 'Connection %' and show_connection_percentage:
                    # Special sorting for percentage column
                    df['Connection_Numeric'] = df['Connection %'].str.rstrip('%').astype(float)
                    df = df.sort_values('Connection_Numeric', ascending=ascending)
                    df = df.drop('Connection_Numeric', axis=1)
                else:
                    df = df.sort_values(sort_by, ascending=ascending)

                # Display results with enhanced formatting
                st.dataframe(df, use_container_width=True, height=400)

                # Enhanced summary statistics
                with st.expander("📊 Search Results Connection Analysis"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Results", len(filtered_objects))
                        connected_count = len(df[df['Connection Status'] == 'Connected'])
                        st.metric("Connected Objects", connected_count)

                    with col2:
                        isolated_count = len(df[df['Connection Status'] == 'Isolated'])
                        st.metric("Isolated Objects", isolated_count)
                        if len(filtered_objects) > 0:
                            connected_pct = (connected_count / len(filtered_objects)) * 100
                            st.metric("Connection Rate", f"{connected_pct:.1f}%")

                    with col3:
                        st.metric("Avg Connections", f"{df['Connections'].mean():.1f}")
                        st.metric("Max Connections", df['Connections'].max())

                    with col4:
                        # Type distribution in results
                        type_counts = df['Type'].value_counts()
                        st.write("**Top Types Found:**")
                        for obj_type, count in type_counts.head(3).items():
                            st.write(f"• {obj_type}: {count}")

                    # Connection distribution chart
                    if len(filtered_objects) > 1:
                        st.markdown("**Connection Distribution in Results:**")
                        fig_hist = px.histogram(
                            df,
                            x='Connections',
                            nbins=20,
                            title="Connection Count Distribution",
                            labels={'Connections': 'Number of Connections', 'count': 'Number of Objects'}
                        )
                        fig_hist.update_layout(height=300)
                        st.plotly_chart(fig_hist, use_container_width=True)

                # Enhanced export options
                st.markdown("---")
                col1, col2, col3 = st.columns(3)

                with col1:
                    # CSV export with connection analysis
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results with Connection Analysis (CSV)",
                        data=csv,
                        file_name=f"sap_bw_search_connection_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                with col2:
                    # Connection summary export
                    if st.button("📊 Export Connection Summary"):
                        summary_report = generate_search_connection_summary(self, df, connection_filter_type)
                        st.download_button(
                            label="📥 Download Connection Summary (TXT)",
                            data=summary_report,
                            file_name=f"connection_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )

                with col3:
                    # Quick analysis actions
                    if st.button("🎯 Visualize These Results"):
                        st.info("💡 Consider using 3D Network Visualization with similar filters")
                    if st.button("📊 Detailed Analysis"):
                        st.info("💡 For specific objects, use InfoCube or InfoObject Impact Analysis")

                if len(filtered_objects) >= max_results:
                    st.warning(f"⚠️ Results limited to {max_results}. Increase limit or refine search to see more.")
            else:
                st.info("No objects match your search criteria.")

                # Enhanced suggestions for no results
                st.markdown("**💡 Search Tips:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("• Try broader search terms")
                    st.write("• Remove or adjust filters")
                    st.write("• Check InfoArea or Owner filters")
                with col2:
                    st.write("• Adjust connection range")
                    st.write("• Try different connection filter types")
                    st.write(f"• Current avg connections: {connection_stats['average_connections']:.1f}")
