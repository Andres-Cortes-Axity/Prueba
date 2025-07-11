import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json
from backend.infocube_analysis import analyze_infocube_connections
from backend.infocube_analysis import create_infocube_connection_3d_visualization
from backend.infocube_analysis import prepare_infocube_connection_csv
from backend.infocube_analysis import generate_infocube_connection_report
from connectors.source_detectors import get_source_system_info


def show_infocube_connection_analysis(self):
    """NEW METHOD: Show InfoCube Connection Analysis page"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("🧊 InfoCube Connection Analysis with Complete Source Tracing")
    st.markdown("**Analyze all connections for a specific InfoCube including InfoSources, DataSources, and complete data flow**")

    # Get all InfoCubes for selection
    cube_list = []
    if 'CUBE' in st.session_state.global_inventory:
        cube_list = [obj['name'] for obj in st.session_state.global_inventory['CUBE']]

    if not cube_list:
        st.error("❌ No InfoCubes found in the dataset")
        return

    # Sort InfoCubes alphabetically
    cube_list.sort()

    # Controls section
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🧊 Select InfoCube")

        # Search within InfoCubes
        search_cube = st.text_input(
            "🔍 Search InfoCubes:",
            placeholder="Type to filter InfoCubes...",
            help="Filter the InfoCube list"
        )

        # Filter InfoCubes based on search
        filtered_cube_list = [cube for cube in cube_list
                              if search_cube.lower() in cube.lower()] if search_cube else cube_list

        if not filtered_cube_list:
            st.warning("No InfoCubes match your search")
            return

        selected_cube = st.selectbox(
            "Choose InfoCube:",
            options=filtered_cube_list,
            help=f"Select from {len(filtered_cube_list)} InfoCubes"
        )

        st.info(f"🧊 **Selected:** {selected_cube}")

    with col2:
        st.subheader("🔧 Analysis Settings")

        analysis_depth = st.slider(
            "Connection Depth:",
            min_value=1,
            max_value=5,
            value=3,
            help="How many levels of connections to analyze"
        )

        include_all_sources = st.checkbox(
            "Include All Source Types",
            value=True,
            help="Include DataSources, InfoSources, and all upstream connections"
        )

        connection_types = st.multiselect(
            "Connection Types to Analyze:",
            options=['transformation', 'usage_dimension', 'usage_keyfigure', 'source_connection', 'all'],
            default=['transformation', 'usage_dimension', 'usage_keyfigure', 'source_connection'],
            help="Select which relationship types to include"
        )

        if 'all' in connection_types:
            connection_types = ['transformation', 'usage_dimension', 'usage_keyfigure', 'source_connection']

    with col3:
        st.subheader("📊 Display Options")

        group_by_type = st.checkbox(
            "Group by Object Type",
            value=True,
            help="Organize results by object type"
        )

        show_details = st.checkbox(
            "Show Detailed Information",
            value=True,
            help="Include owner, InfoArea, source systems, etc."
        )

        render_3d = st.checkbox(
            "Generate 3D Visualization",
            value=True,
            help="Create 3D network view of InfoCube connections"
        )

        show_data_lineage = st.checkbox(
            "Show Data Lineage Path",
            value=True,
            help="Display complete path from sources to InfoCube"
        )

    st.markdown("---")

    # Analyze button
    if st.button("🧊 Analyze InfoCube Connections & Sources", type="primary"):
        with st.spinner(f"🔄 Analyzing all connections for InfoCube: {selected_cube}..."):

            # Perform the InfoCube connection analysis
            connection_results = analyze_infocube_connections(
                self, selected_cube, analysis_depth, include_all_sources,
                connection_types, show_data_lineage
            )

            if not connection_results:
                st.warning(f"No connections found for InfoCube: {selected_cube}")
                return

            # Display results
            display_infocube_connection_analysis(
                self, selected_cube, connection_results, group_by_type,
                show_details, render_3d, show_data_lineage
            )


def display_infocube_connection_analysis(self, cube_name, results, group_by_type, show_details, render_3d, show_lineage):
    """NEW METHOD: Display the InfoCube connection analysis results"""

    # Summary metrics
    st.success("✅ InfoCube Connection Analysis Complete!")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🧊 Target InfoCube", cube_name)
    with col2:
        st.metric("🔗 Connected Objects", results['total_objects'])
    with col3:
        st.metric("↔️ Relationships", results['total_relationships'])
    with col4:
        lineage_count = len(results.get('data_lineage_paths', []))
        st.metric("🛤️ Data Lineage Paths", lineage_count)
    with col5:
        st.metric("🔍 Analysis Depth", results['analysis_depth'])

    st.markdown("---")

    # Data lineage analysis - NEW SECTION
    if show_lineage and results.get('data_lineage_paths'):
        st.subheader("🛤️ Complete Data Lineage Analysis")
        st.caption("Tracing data flow from sources to InfoCube")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📊 Lineage Summary**")

            source_systems = set()
            total_paths = len(results['data_lineage_paths'])
            path_lengths = [path['path_length'] for path in results['data_lineage_paths']]

            for path in results['data_lineage_paths']:
                source_name = path['source']
                source_system = get_source_system_info(self, source_name)
                source_systems.add(source_system)

            summary_data = {
                'Total Lineage Paths': total_paths,
                'Source Systems': len(source_systems),
                'Avg Path Length': f"{np.mean(path_lengths):.1f}" if path_lengths else "0",
                'Max Path Length': max(path_lengths) if path_lengths else 0,
                'Direct Connections': len([p for p in results['data_lineage_paths'] if p['path_length'] == 2])
            }

            for key, value in summary_data.items():
                st.write(f"• **{key}**: {value}")

        with col2:
            st.markdown("**🗂️ Source Systems Involved**")
            system_counts = {}
            for path in results['data_lineage_paths']:
                source_system = get_source_system_info(self, path['source'])
                system_counts[source_system] = system_counts.get(source_system, 0) + 1

            for system, count in sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                st.write(f"• **{system}**: {count} connection{'s' if count != 1 else ''}")

        # Detailed lineage paths
        with st.expander("🔍 Detailed Data Lineage Paths", expanded=False):
            lineage_details = []
            for path in results['data_lineage_paths'][:20]:  # Show top 20
                intermediate_str = " → ".join([obj['object_name'] for obj in path['intermediate_objects']])
                if not intermediate_str:
                    intermediate_str = "Direct Connection"

                lineage_details.append({
                    'Source': path['source'],
                    'Source System': get_source_system_info(self, path['source']),
                    'Path': f"{path['source']} → {intermediate_str} → {cube_name}",
                    'Path Length': path['path_length'],
                    'Intermediate Objects': len(path['intermediate_objects'])
                })

            if lineage_details:
                df_lineage = pd.DataFrame(lineage_details)
                st.dataframe(df_lineage, use_container_width=True, height=300)
                if len(results['data_lineage_paths']) > 20:
                    st.caption(f"Showing top 20 of {len(results['data_lineage_paths'])} lineage paths")

    st.markdown("---")

    # Source system analysis
    if results['connected_objects'].get('DS'):
        st.subheader("📡 Source System Analysis")
        st.caption("DataSources and InfoSources feeding the InfoCube")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🌐 Source Systems Overview**")
            source_summary = {}

            for ds_obj in results['connected_objects']['DS']:
                source_system = ds_obj.get('source_system', 'Unknown')
                infosource_type = ds_obj.get('infosource_type', 'DataSource')

                if source_system not in source_summary:
                    source_summary[source_system] = {'count': 0, 'types': set()}

                source_summary[source_system]['count'] += 1
                source_summary[source_system]['types'].add(infosource_type)

            summary_data = []
            for system, info in source_summary.items():
                summary_data.append({
                    'Source System': system,
                    'DataSources/InfoSources': info['count'],
                    'Types': ', '.join(sorted(info['types']))
                })

            if summary_data:
                df_sources = pd.DataFrame(summary_data)
                df_sources = df_sources.sort_values('DataSources/InfoSources', ascending=False)
                st.dataframe(df_sources, use_container_width=True, height=200)

        with col2:
            st.markdown("**📡 InfoSource Type Distribution**")
            type_counts = {}
            for ds_obj in results['connected_objects']['DS']:
                infosource_type = ds_obj.get('infosource_type', 'DataSource')
                type_counts[infosource_type] = type_counts.get(infosource_type, 0) + 1

            for infosource_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                st.write(f"• **{infosource_type}**: {count}")

    st.markdown("---")

    # Connection direction analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Data Feeding InfoCube")
        st.caption("Objects that provide data TO this InfoCube")

        feeding_objects = []
        for rel in results['relationships']:
            if rel['direction'] == 'incoming':
                source_node = st.session_state.graph.nodes.get(rel['source'])
                if source_node:
                    feeding_objects.append({
                        'Object': source_node['name'],
                        'Type': source_node['type_name'],
                        'Connection Type': rel['type'].replace('_', ' ').title(),
                        'Depth': rel['depth'],
                        'Source System': rel.get('source_system', '') if source_node['type'] == 'DS' else ''
                    })

        if feeding_objects:
            df_feeding = pd.DataFrame(feeding_objects)
            st.dataframe(df_feeding, use_container_width=True, height=200)
            st.caption(f"Showing {len(feeding_objects)} objects feeding data")
        else:
            st.info("No feeding dependencies found")

    with col2:
        st.subheader("📉 InfoCube Data Usage")
        st.caption("Objects that USE data FROM this InfoCube")

        consuming_objects = []
        for rel in results['relationships']:
            if rel['direction'] == 'outgoing':
                target_node = st.session_state.graph.nodes.get(rel['target'])
                if target_node:
                    consuming_objects.append({
                        'Object': target_node['name'],
                        'Type': target_node['type_name'],
                        'Connection Type': rel['type'].replace('_', ' ').title(),
                        'Depth': rel['depth']
                    })

        if consuming_objects:
            df_consuming = pd.DataFrame(consuming_objects)
            st.dataframe(df_consuming, use_container_width=True, height=200)
            st.caption(f"Showing {len(consuming_objects)} objects consuming data")
        else:
            st.info("No consuming objects found")

    st.markdown("---")

    # Detailed object analysis
    if group_by_type:
        st.subheader("📊 Connected Objects by Type (Enhanced with Source Info)")

        if not results['connected_objects']:
            st.warning("No connected objects found")
            return

        for obj_type, objects in results['connected_objects'].items():
            if not objects:
                continue

            config = self.object_types[obj_type]

            with st.expander(f"{config['icon']} {config['name']} ({len(objects)} objects)", expanded=True):

                if show_details:
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

                        # Enhanced info for DataSources/InfoSources
                        if obj_type == 'DS':
                            row_data['Source System'] = obj.get('source_system', 'Unknown')
                            row_data['InfoSource Type'] = obj.get('infosource_type', 'DataSource')

                        detail_data.append(row_data)

                    df_detail = pd.DataFrame(detail_data)
                    df_detail = df_detail.sort_values('Total Connections', ascending=False)
                    st.dataframe(df_detail, use_container_width=True)

                else:
                    # Simple view with enhanced source info
                    if obj_type == 'DS':
                        object_display = []
                        for obj in objects:
                            source_sys = obj.get('source_system', 'Unknown')
                            infosource_type = obj.get('infosource_type', 'DS')
                            object_display.append(f"{obj['name']} ({source_sys} - {infosource_type})")
                        st.write(", ".join(object_display))
                    else:
                        object_names = [obj['name'] for obj in objects]
                        st.write(", ".join(object_names))

    # 3D Visualization for InfoCube connections
    if render_3d and results['total_objects'] > 0:
        st.markdown("---")
        st.subheader("🧊 3D InfoCube Connection Visualization")

        # Create focused dataset for visualization
        focused_objects = []

        # Add the target InfoCube
        target_cube_data = None
        for obj in st.session_state.global_inventory.get('CUBE', []):
            if obj['name'] == cube_name:
                target_cube_data = obj.copy()
                target_cube_data['node_id'] = f"CUBE:{cube_name}"
                target_cube_data['is_target'] = True
                break

        if target_cube_data:
            focused_objects.append(target_cube_data)

        # Add all connected objects
        for obj_type, objects in results['connected_objects'].items():
            for obj in objects:
                obj_copy = obj.copy()
                obj_copy['is_target'] = False
                focused_objects.append(obj_copy)

        # Create enhanced 3D visualization
        fig = create_infocube_connection_3d_visualization(
            self, focused_objects, results['relationships'], cube_name
        )

        if fig:
            st.plotly_chart(fig, use_container_width=True, height=800)

            st.info("""
            🎮 **3D InfoCube Connection Navigation:**
            - **🧊 Gold Cube** = Target InfoCube
            - **⬅️ Green Lines** = Data feeding the InfoCube
            - **➡️ Red Lines** = InfoCube data being used
            - **🔵 Blue Lines** = Source connections (from DataSources/InfoSources)
            - **📡 DataSource nodes** = Enhanced with source system and InfoSource type info
            - **Node Size** = Reflects total connections
            - **Hover** for detailed connection and source information
            """)

    # Export options with InfoCube-specific information
    st.markdown("---")
    st.subheader("📤 Export InfoCube Connection Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Export Connections (CSV)"):
            csv_data = prepare_infocube_connection_csv(self, results)
            st.download_button(
                label="📥 Download InfoCube Connections (CSV)",
                data=csv_data,
                file_name=f"infocube_connections_{cube_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    with col2:
        if st.button("📄 Export Full Analysis (JSON)"):
            json_data = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="📥 Download Full Analysis (JSON)",
                data=json_data,
                file_name=f"infocube_analysis_{cube_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with col3:
        if st.button("📋 Generate Connection Report"):
            report = generate_infocube_connection_report(self, cube_name, results)
            st.download_button(
                label="📥 Download Connection Report (TXT)",
                data=report,
                file_name=f"infocube_report_{cube_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
