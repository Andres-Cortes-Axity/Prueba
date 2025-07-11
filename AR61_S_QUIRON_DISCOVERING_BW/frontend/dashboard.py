import streamlit as st
import pandas as pd
import plotly.express as px
from backend.infocube_analysis import calculate_connection_percentages
from connectors.source_detectors import get_source_system_info


def show_analytics_dashboard(self):
    """Show analytics dashboard with comprehensive connection percentage analysis"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("📊 Enhanced Analytics Dashboard with Connection Analysis")

    # Generate enhanced statistics including connection percentages
    stats = st.session_state.dataset_stats
    connection_stats = calculate_connection_percentages(self)

    # Key metrics row with connection percentages
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📦 Total Objects", f"{stats['total_objects']:,}")
    with col2:
        st.metric("🔗 Relationships", f"{stats['total_relationships']:,}")
    with col3:
        connected_pct = connection_stats['overall_connected_percentage']
        st.metric("🔗 Connected Objects", f"{connected_pct:.1f}%",
                  help=f"{connection_stats['connected_objects']:,} of {connection_stats['total_objects']:,} objects have connections")
    with col4:
        density = stats.get('graph_density', 0)
        st.metric("🌐 Network Density", f"{density:.4f}")
    with col5:
        isolated_pct = connection_stats['isolated_percentage']
        st.metric("🚫 Isolated Objects", f"{isolated_pct:.1f}%",
                  help=f"{connection_stats['isolated_objects']:,} objects have no connections")

    st.markdown("---")

    # Enhanced connection percentage analysis
    st.subheader("🔗 Connection Distribution Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Overall Connection Status**")

        # Create connection status pie chart
        connection_labels = ['Connected Objects', 'Isolated Objects']
        connection_values = [connection_stats['connected_objects'], connection_stats['isolated_objects']]
        connection_colors = ['#00FF7F', '#FF6B6B']  # Green for connected, Red for isolated

        fig_connection = px.pie(
            values=connection_values,
            names=connection_labels,
            color_discrete_sequence=connection_colors,
            title="Connection Status Distribution"
        )
        fig_connection.update_traces(textposition='inside', textinfo='percent+label')
        fig_connection.update_layout(
            font=dict(size=12),
            showlegend=True,
            height=300
        )
        st.plotly_chart(fig_connection, use_container_width=True)

        # Connection summary table
        summary_data = {
            'Status': ['Connected', 'Isolated', 'Total'],
            'Count': [
                f"{connection_stats['connected_objects']:,}",
                f"{connection_stats['isolated_objects']:,}",
                f"{connection_stats['total_objects']:,}"
            ],
            'Percentage': [
                f"{connection_stats['overall_connected_percentage']:.1f}%",
                f"{connection_stats['isolated_percentage']:.1f}%",
                "100.0%"
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**📈 Connection Level Distribution**")

        # Create connection level histogram
        connection_levels = connection_stats['connection_level_distribution']
        level_labels = list(connection_levels.keys())
        level_values = list(connection_levels.values())

        fig_levels = px.bar(
            x=level_labels,
            y=level_values,
            title="Objects by Connection Count",
            labels={'x': 'Connection Range', 'y': 'Number of Objects'},
            color=level_values,
            color_continuous_scale='Viridis'
        )
        fig_levels.update_layout(
            xaxis_title="Connection Range",
            yaxis_title="Number of Objects",
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig_levels, use_container_width=True)

        # Connection level summary
        st.markdown("**Connection Level Breakdown:**")
        for level, count in connection_levels.items():
            percentage = (count / connection_stats['total_objects']) * 100
            st.write(f"• **{level}**: {count:,} objects ({percentage:.1f}%)")

    st.markdown("---")

    # Enhanced object type analysis with connection percentages
    st.subheader("📊 Object Type Connection Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Objects by Type**")
        if stats['object_type_counts']:
            # Filter out empty types
            filtered_counts = {k: v for k, v in stats['object_type_counts'].items() if v > 0}
            type_names = [self.object_types[k]['name'] for k in filtered_counts.keys()]

            fig = px.pie(
                values=list(filtered_counts.values()),
                names=type_names,
                color_discrete_sequence=[self.object_types[k]['color']
                                         for k in filtered_counts.keys()],
                title="Object Distribution by Type"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**🔗 Connection Rates by Object Type**")

        # Calculate connection percentages by object type
        type_connection_stats = connection_stats['by_object_type']

        if type_connection_stats:
            # Create connection rate bar chart
            obj_types = []
            connection_rates = []
            colors = []

            for obj_type, type_stats in type_connection_stats.items():
                if type_stats['total'] > 0:
                    config = self.object_types[obj_type]
                    obj_types.append(config['name'])
                    connection_rates.append(type_stats['connected_percentage'])
                    colors.append(config['color'])

            fig_rates = px.bar(
                x=obj_types,
                y=connection_rates,
                title="Connection Rate by Object Type",
                labels={'x': 'Object Type', 'y': 'Connection Rate (%)'},
                color=colors,
                color_discrete_map={obj_types[i]: colors[i] for i in range(len(obj_types))}
            )
            fig_rates.update_layout(
                xaxis_title="Object Type",
                yaxis_title="Connection Rate (%)",
                showlegend=False,
                height=300
            )
            st.plotly_chart(fig_rates, use_container_width=True)

            # Connection rate table
            rate_data = []
            for obj_type, type_stats in type_connection_stats.items():
                if type_stats['total'] > 0:
                    config = self.object_types[obj_type]
                    rate_data.append({
                        'Type': f"{config['icon']} {config['name']}",
                        'Total': f"{type_stats['total']:,}",
                        'Connected': f"{type_stats['connected']:,}",
                        'Rate': f"{type_stats['connected_percentage']:.1f}%"
                    })

            df_rates = pd.DataFrame(rate_data)
            df_rates = df_rates.sort_values('Rate', ascending=False, key=lambda x: x.str.rstrip('%').astype(float))
            st.dataframe(df_rates, use_container_width=True, hide_index=True)


# Enhanced analysis section with connection insights
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🧊 InfoCube Analysis")
        cube_count = len(st.session_state.global_inventory.get('CUBE', []))
        st.metric("Total InfoCubes", f"{cube_count:,}")

        if cube_count > 0:
            # Calculate InfoCube connection statistics
            cube_connections = connection_stats['by_object_type'].get('CUBE', {})
            if cube_connections and cube_connections.get('total', 0) > 0:
                st.metric("InfoCube Connection Rate", f"{cube_connections['connected_percentage']:.1f}%")
                st.metric("Avg Connections per InfoCube", f"{cube_connections['average_connections']:.1f}")

            st.success("✅ InfoCube Connection Analysis Available")
            st.info("💡 Use the InfoCube Connection Analysis page for detailed dependency mapping")
        else:
            st.warning("⚠️ No InfoCubes found")

    with col2:
        st.subheader("📡 Source System Analysis")
        ds_count = len(st.session_state.global_inventory.get('DS', []))
        st.metric("DataSources/InfoSources", f"{ds_count:,}")

        if ds_count > 0:
            # Calculate DataSource connection statistics
            ds_connections = connection_stats['by_object_type'].get('DS', {})
            if ds_connections and ds_connections.get('total', 0) > 0:
                st.metric("DataSource Connection Rate", f"{ds_connections['connected_percentage']:.1f}%")

            # Analyze source systems
            source_systems = set()
            for ds_obj in st.session_state.global_inventory.get('DS', []):
                source_system = get_source_system_info(self, ds_obj['name'])
                source_systems.add(source_system)

            st.metric("Unique Source Systems", len(source_systems))

            with st.expander("Source Systems Detected"):
                for system in sorted(source_systems):
                    # Count DataSources per system
                    system_count = sum(1 for ds_obj in st.session_state.global_inventory.get('DS', [])
                                       if get_source_system_info(self, ds_obj['name']) == system)
                    st.write(f"• {system}: {system_count} DataSources")

    # Connection insights and recommendations
    st.markdown("---")
    st.subheader("🔍 Connection Insights & Recommendations")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Network Health Analysis**")

        connected_rate = connection_stats['overall_connected_percentage']
        isolated_rate = connection_stats['isolated_percentage']

        if connected_rate >= 80:
            st.success(f"🟢 **Excellent Network Connectivity** ({connected_rate:.1f}%)")
            st.write("• Most objects are well integrated")
            st.write("• Strong data flow patterns")
        elif connected_rate >= 60:
            st.info(f"🟡 **Good Network Connectivity** ({connected_rate:.1f}%)")
            st.write("• Majority of objects are connected")
            st.write("• Some isolated objects to review")
        else:
            st.warning(f"🔴 **Limited Network Connectivity** ({connected_rate:.1f}%)")
            st.write("• Many isolated objects detected")
            st.write("• Consider reviewing data architecture")

        if isolated_rate > 20:
            st.warning(f"⚠️ **High Isolation Rate**: {isolated_rate:.1f}% of objects are isolated")
            st.write("• May indicate unused or legacy objects")
            st.write("• Consider cleanup or integration")

        # Most connected object insight
        if connection_stats['most_connected_object']:
            most_connected = connection_stats['most_connected_object']
            st.info(
                f"🏆 **Most Connected Object**: {most_connected['name']} ({most_connected['type']}) with {most_connected['connections']} connections")

    with col2:
        st.markdown("**💡 Analysis Recommendations**")

        recommendations = []

        # Connection-based recommendations
        if isolated_rate > 15:
            recommendations.append("🔍 **Investigate isolated objects** - Use Object Explorer to find unused objects")

        if connected_rate < 70:
            recommendations.append("🔗 **Review connectivity patterns** - Many objects lack proper integration")

        # InfoCube recommendations
        if cube_count > 0:
            cube_stats = connection_stats['by_object_type'].get('CUBE', {})
            if cube_stats and cube_stats.get('connected_percentage', 0) < 90:
                recommendations.append("🧊 **Analyze InfoCube connections** - Some InfoCubes may lack proper data sources")

        # DataSource recommendations
        if ds_count > 0:
            ds_stats = connection_stats['by_object_type'].get('DS', {})
            if ds_stats and ds_stats.get('connected_percentage', 0) < 80:
                recommendations.append("📡 **Review DataSource usage** - Some DataSources may be unused")

        # Performance recommendations
        total_objects = stats['total_objects']
        if total_objects > 10000:
            recommendations.append("⚡ **Enable performance optimizations** for large dataset visualization")

        # Feature usage recommendations
        iobj_count = len(st.session_state.global_inventory.get('IOBJ', []))
        if iobj_count > 0:
            recommendations.append("🏷️ **Use InfoObject Impact Analysis** to understand InfoObject usage patterns")

        if not recommendations:
            recommendations.append("✅ **Network analysis looks good** - Continue with detailed object analysis")

        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")

    # Performance and dataset insights
    st.markdown("---")
    st.subheader("⚡ Performance & Dataset Insights")

    total_objects = stats['total_objects']

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📈 Dataset Size Analysis**")
        if total_objects > 50000:
            st.error("🔥 **Very Large Dataset**")
            st.write("- Use filtered views only")
            st.write("- Enable smart sampling")
            st.write("- Focus on high-connection objects")
        elif total_objects > 20000:
            st.warning("⚡ **Large Dataset**")
            st.write("- Use performance mode")
            st.write("- Enable smart sampling")
            st.write("- Limit 3D objects < 2000")
        elif total_objects > 10000:
            st.info("📊 **Medium Dataset**")
            st.write("- Performance mode recommended")
            st.write("- Use filtered views")
            st.write("- Connection filtering available")
        else:
            st.success("✅ **Small Dataset**")
            st.write("- Full features available")
            st.write("- No performance limits")
            st.write("- All visualizations enabled")

    with col2:
        st.markdown("**🔗 Connection Complexity**")
        avg_connections = connection_stats['average_connections']
        max_connections = connection_stats['max_connections']

        st.metric("Average Connections", f"{avg_connections:.1f}")
        st.metric("Maximum Connections", f"{max_connections}")

        if avg_connections > 10:
            st.info("🔗 **Highly Connected Network**")
            st.write("- Rich data relationships")
            st.write("- Use connection filtering")
        elif avg_connections > 5:
            st.success("✅ **Well Connected Network**")
            st.write("- Good data integration")
            st.write("- Balanced connectivity")
        else:
            st.warning("📊 **Sparse Network**")
            st.write("- Limited connections")
            st.write("- Consider data integration")

    with col3:
        st.markdown("**🎯 Visualization Options**")
        st.write("**Available with Connection %:**")
        st.write("• 🎯 3D Network with connection filtering")
        st.write("• 🔍 Object Explorer with connection ranges")
        st.write("• 🧊 InfoCube analysis with connection rates")
        st.write("• 📊 Connection percentage charts")

        # Quick action buttons
        if st.button("🔍 Explore Connected Objects", help="Filter objects by connection count"):
            st.info("💡 Use the Object Explorer page with connection range filters")

        if st.button("🎯 Visualize Network", help="Create 3D visualization"):
            st.info("💡 Use the 3D Network Visualization page with connection-based sampling")

    # Detailed breakdown
    st.markdown("---")
    st.subheader("🔍 Detailed Breakdown")

    # Create detailed stats table
    detailed_stats = []
    for obj_type, count in stats['object_type_counts'].items():
        if count > 0:
            config = self.object_types[obj_type]

            # Calculate average connections
            avg_connections = 0
            if obj_type in st.session_state.global_inventory:
                total_connections = 0
                for obj in st.session_state.global_inventory[obj_type]:
                    node_id = f"{obj_type}:{obj['name']}"
                    if node_id in st.session_state.graph.nodes:
                        total_connections += st.session_state.graph.degree(node_id)
                avg_connections = total_connections / count if count > 0 else 0

            detailed_stats.append({
                'Icon': config['icon'],
                'Object Type': config['name'],
                'Category': config['category'],
                'Count': f"{count:,}",
                'Avg Connections': f"{avg_connections:.1f}",
                'Priority': '🔥' if config['priority'] == 3 else '⚡' if config['priority'] == 2 else '💡'
            })

    if detailed_stats:
        df = pd.DataFrame(detailed_stats)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Connection analysis
    st.markdown("---")
    st.subheader("🔗 Connection Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Connection Types Distribution**")
        connection_types = {}
        for rel in st.session_state.relationships:
            rel_type = rel['type']
            connection_types[rel_type] = connection_types.get(rel_type, 0) + 1

        if connection_types:
            for conn_type, count in sorted(connection_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(st.session_state.relationships)) * 100
                st.write(f"• **{conn_type.replace('_', ' ').title()}**: {count:,} ({percentage:.1f}%)")

    with col2:
        st.markdown("**Top Connected Objects**")
        # Find top connected objects across all types
        top_connected = []
        for obj_type, objects in st.session_state.global_inventory.items():
            for obj in objects:
                node_id = f"{obj_type}:{obj['name']}"
                if node_id in st.session_state.graph.nodes:
                    connections = st.session_state.graph.degree(node_id)
                    if connections > 0:
                        top_connected.append({
                            'name': obj['name'],
                            'type': obj['type_name'],
                            'connections': connections
                        })

        # Sort and show top 10
        top_connected.sort(key=lambda x: x['connections'], reverse=True)
        for obj in top_connected[:10]:
            st.write(f"• **{obj['name']}** ({obj['type']}): {obj['connections']} connections")

    # Recommendations
    st.markdown("---")
    st.subheader("💡 Analysis Recommendations")

    recommendations = []

    # InfoCube recommendations
    if cube_count > 0:
        recommendations.append("🧊 **Use InfoCube Connection Analysis** for detailed dependency mapping of your InfoCubes")

    # Performance recommendations
    if total_objects > 10000:
        recommendations.append("⚡ **Enable performance optimizations** for large dataset visualization")

    # Source system recommendations
    if ds_count > 0:
        recommendations.append("📡 **Analyze source system dependencies** to understand data lineage")

    # InfoObject recommendations
    iobj_count = len(st.session_state.global_inventory.get('IOBJ', []))
    if iobj_count > 0:
        recommendations.append("🏷️ **Use InfoObject Impact Analysis** to understand InfoObject usage patterns")

    for rec in recommendations:
        st.info(rec)
