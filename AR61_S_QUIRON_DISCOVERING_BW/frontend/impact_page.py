import streamlit as st
from backend.impact_analysis import analyze_infoobject_impact_with_sources, display_impact_analysis_with_sources


def show_infoobject_impact_analysis(self):
    """Show InfoObject Impact Analysis page with source connection tracking - FULL FEATURE"""
    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data first from the Home page")
        return

    st.header("🔍 InfoObject Impact Analysis with Source Connections")
    st.markdown("**Analyze dependencies, impact, and trace connections back to data sources**")

    # Get all InfoObjects for selection
    iobj_list = []
    if 'IOBJ' in st.session_state.global_inventory:
        iobj_list = [obj['name'] for obj in st.session_state.global_inventory['IOBJ']]

    if not iobj_list:
        st.error("❌ No InfoObjects found in the dataset")
        return

    # Sort InfoObjects alphabetically
    iobj_list.sort()

    # Controls section - Simplified and focused on source connections
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🎯 Select InfoObject")

        # Search within InfoObjects
        search_iobj = st.text_input(
            "🔍 Search InfoObjects:",
            placeholder="Type to filter InfoObjects...",
            help="Filter the InfoObject list"
        )

        # Filter InfoObjects based on search
        filtered_iobj_list = [iobj for iobj in iobj_list
                              if search_iobj.lower() in iobj.lower()] if search_iobj else iobj_list

        if not filtered_iobj_list:
            st.warning("No InfoObjects match your search")
            return

        selected_iobj = st.selectbox(
            "Choose InfoObject:",
            options=filtered_iobj_list,
            help=f"Select from {len(filtered_iobj_list)} InfoObjects"
        )

        st.info(f"🏷️ **Selected:** {selected_iobj}")

    with col2:
        st.subheader("🔧 Analysis Settings")

        analysis_depth = st.slider(
            "Connection Depth:",
            min_value=1,
            max_value=5,
            value=3,
            help="How many levels of connections to analyze"
        )

        include_source_tracing = st.checkbox(
            "Enable Source Tracing",
            value=True,
            help="Trace connections back to DataSources and source systems"
        )

        show_connection_types = st.multiselect(
            "Connection Types to Show:",
            options=['transformation', 'usage_dimension', 'usage_keyfigure', 'source_connection', 'all'],
            default=['transformation', 'usage_dimension', 'source_connection'],
            help="Filter by relationship types"
        )

        if 'all' in show_connection_types:
            show_connection_types = ['transformation', 'usage_dimension', 'usage_keyfigure', 'source_connection']

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
            help="Include owner, InfoArea, etc."
        )

        render_3d = st.checkbox(
            "Generate 3D Visualization",
            value=True,
            help="Create 3D network view of connections"
        )

        # Source analysis options
        st.markdown("**Source Analysis:**")
        show_source_systems = st.checkbox(
            "Show Source Systems",
            value=True,
            help="Display source system information"
        )

    st.markdown("---")

    # Analyze button
    if st.button("🔍 Analyze InfoObject Impact & Sources", type="primary"):
        with st.spinner(f"🔄 Analyzing impact and source connections for InfoObject: {selected_iobj}..."):

            # Perform the enhanced impact analysis with source tracing
            impact_results = analyze_infoobject_impact_with_sources(
                self, selected_iobj, analysis_depth, include_source_tracing, show_connection_types, show_source_systems
            )

            if not impact_results:
                st.warning(f"No connections found for InfoObject: {selected_iobj}")
                return

            # Display results
            display_impact_analysis_with_sources(
                self, selected_iobj, impact_results, group_by_type, show_details, render_3d
            )
