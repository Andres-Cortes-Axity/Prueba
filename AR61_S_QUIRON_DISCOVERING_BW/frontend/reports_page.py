import streamlit as st
import json
from datetime import datetime

from connectors.source_detectors import get_source_system_info
from backend.reports import get_sample_for_export
from backend.reports import prepare_objects_csv_export
from backend.reports import generate_connection_analysis_report


def show_reports_page(self):
    """Show reports page with export options"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("📋 Reports & Export")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Quick Reports")

        # Dataset summary
        if st.button("📈 Dataset Summary Report"):
            stats = st.session_state.dataset_stats

            summary = f"""
# SAP BW Dataset Summary Report

**Analysis Date:** {stats.get('load_timestamp', 'Unknown')}
**Total Objects:** {stats['total_objects']:,}
**Total Relationships:** {stats['total_relationships']:,}
**Network Density:** {stats.get('graph_density', 0):.4f}

## Object Type Breakdown:
"""
            for obj_type, count in stats['object_type_counts'].items():
                if count > 0:
                    config = self.object_types[obj_type]
                    summary += f"- **{config['name']}**: {count:,} objects\n"

            # Add source system analysis
            ds_count = len(st.session_state.global_inventory.get('DS', []))
            if ds_count > 0:
                summary += "\n## Source System Analysis:\n"
                source_systems = set()
                for ds_obj in st.session_state.global_inventory.get('DS', []):
                    source_system = get_source_system_info(self, ds_obj['name'])
                    source_systems.add(source_system)

                summary += f"- **Total DataSources/InfoSources**: {ds_count:,}\n"
                summary += f"- **Unique Source Systems**: {len(source_systems)}\n"
                for system in sorted(source_systems):
                    summary += f"  - {system}\n"

            # Add InfoCube analysis
            cube_count = len(st.session_state.global_inventory.get('CUBE', []))
            if cube_count > 0:
                summary += "\n## InfoCube Analysis:\n"
                summary += f"- **Total InfoCubes**: {cube_count:,}\n"
                summary += "- **InfoCube Connection Analysis Available**: Yes\n"

            st.text_area("Summary Report", summary, height=400)

            st.download_button(
                label="📥 Download Summary (TXT)",
                data=summary,
                file_name=f"sap_bw_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

        # Connection analysis report
        if st.button("🔗 Connection Analysis Report"):
            report = generate_connection_analysis_report(self)
            st.text_area("Connection Analysis", report, height=300)

            st.download_button(
                label="📥 Download Connection Report (TXT)",
                data=report,
                file_name=f"sap_bw_connections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

    with col2:
        st.subheader("📤 Data Export")

        # JSON export
        if st.button("📤 Export Complete Dataset (JSON)"):
            with st.spinner("Preparing export..."):
                export_data = {
                    'metadata': {
                        'export_timestamp': datetime.now().isoformat(),
                        'total_objects': st.session_state.dataset_stats['total_objects'],
                        'total_relationships': st.session_state.dataset_stats['total_relationships']
                    },
                    'statistics': st.session_state.dataset_stats,
                    'object_counts': {obj_type: len(objects) for obj_type, objects in st.session_state.global_inventory.items()},
                    # Include sample of objects for large datasets
                    'sample_objects': get_sample_for_export(self),
                    'sample_relationships': st.session_state.relationships[:1000]  # Sample relationships
                }

                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    label="📥 Download JSON Export",
                    data=json_str,
                    file_name=f"sap_bw_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                st.success("✅ Export ready for download!")

        # Enhanced CSV export
        if st.button("📊 Export Objects (CSV)"):
            with st.spinner("Preparing CSV export..."):
                csv_data = prepare_objects_csv_export(self)
                st.download_button(
                    label="📥 Download Objects CSV",
                    data=csv_data,
                    file_name=f"sap_bw_objects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                st.success("✅ CSV export ready!")

    # Performance tips
    st.markdown("---")
    st.subheader("💡 Performance Tips")

    total_objects = st.session_state.dataset_stats['total_objects']

    if total_objects > 20000:
        st.warning("""
        **Large Dataset Optimization Tips:**
        - Use filtered 3D views instead of showing all objects at once
        - Enable smart sampling for better performance
        - Focus on specific InfoAreas or object types
        - Use the Object Explorer for detailed searches
        - Export data in smaller chunks if needed
        """)
    else:
        st.success("""
        **Your dataset size is manageable:**
        - Full 3D visualization available
        - All features enabled
        - No performance restrictions
        """)
