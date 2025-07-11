import sys
import pathlib
import streamlit as st
import networkx as nx
import warnings
from connectors.sqlite_connector import load_and_analyze_data
from frontend.dashboard import show_analytics_dashboard
from frontend.home_page import show_home_page
from frontend.impact_page import show_infoobject_impact_analysis
from frontend.infocube_page import show_infocube_connection_analysis
from frontend.object_explorer import show_object_explorer
from frontend.optimization_page import show_optimized_3d_visualization_page
from frontend.reports_page import show_reports_page
warnings.filterwarnings('ignore')
# 👇 Pon esto al principio de frontend/app.py


ROOT = pathlib.Path(__file__).resolve().parent.parent  # sube a la raíz
sys.path.insert(0, str(ROOT))                         # prioridad máxima

# Page configuration
st.set_page_config(
    page_title="🎯 SAP BW InfoCube Connection Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


class SAP_BW_Enhanced_Analyzer:
    """
    Enhanced SAP BW 3D Network Analyzer with InfoCube Connection Analysis

    New Features:
    - InfoCube Connection Analysis - analyze all connections for a specific InfoCube
    - InfoSource/DataSource integration and tracing
    - Complete connection mapping including all source systems
    - Enhanced filtering and visualization
    """

    def __init__(self):
        # Enhanced object type definitions with valid Plotly symbols
        self.object_types = {
            'CUBE': {
                'name': 'InfoCube', 'table': 'RSDCUBE', 'key_field': 'INFOCUBE',
                'color': '#FF6B6B', 'category': 'Provider', 'shape': 'diamond',
                'size_base': 25, 'icon': '🧊', 'z_layer': 3, 'priority': 3
            },
            'ADSO': {
                'name': 'Advanced DSO', 'table': 'RSOADSO', 'key_field': 'ADSONM',
                'color': '#4ECDC4', 'category': 'Provider', 'shape': 'circle',
                'size_base': 22, 'icon': '🏪', 'z_layer': 2.5, 'priority': 3
            },
            'ODSO': {
                'name': 'Classic DSO', 'table': 'RSDODSO', 'key_field': 'ODSOBJECT',
                'color': '#45B7D1', 'category': 'Provider', 'shape': 'diamond-open',
                'size_base': 20, 'icon': '🗄️', 'z_layer': 2, 'priority': 3
            },
            'DS': {
                'name': 'DataSource/InfoSource', 'table': 'ROOSOURCE',
                'key_field': 'OLTPSOURCE',
                'color': '#96CEB4', 'category': 'Source', 'shape': 'square',
                'size_base': 18, 'icon': '📡', 'z_layer': 0, 'priority': 2
            },
            'IOBJ': {
                'name': 'InfoObject', 'table': 'RSDIOBJ', 'key_field': 'IOBJNM',
                'color': '#FFEAA7', 'category': 'Metadata', 'shape': 'circle',
                'size_base': 12, 'icon': '🏷️', 'z_layer': 1, 'priority': 1
            },
            'TRAN': {
                'name': 'Transformation', 'table': 'RSTRAN', 'key_field': 'TRANID',
                'color': '#DDA0DD', 'category': 'Process', 'shape': 'x',
                'size_base': 16, 'icon': '⚙️', 'z_layer': 1.5, 'priority': 2
            }
        }

        # Performance settings
        self.MAX_NODES_3D = 2000
        self.MAX_EDGES_3D = 5000
        self.SAMPLE_SIZE_DEFAULT = 1000

        # Initialize session state
        if 'data_loaded' not in st.session_state:
            st.session_state.data_loaded = False
        if 'global_inventory' not in st.session_state:
            st.session_state.global_inventory = {}
        if 'relationships' not in st.session_state:
            st.session_state.relationships = []
        if 'graph' not in st.session_state:
            st.session_state.graph = nx.DiGraph()
        if 'pos_3d' not in st.session_state:
            st.session_state.pos_3d = {}
        if 'dataset_stats' not in st.session_state:
            st.session_state.dataset_stats = {}
    # Add any remaining helper methods that might be missing

    def create_main_interface(self):
        """Create the main Streamlit interface with complete feature set"""
        # Header
        st.title("🎯 SAP BW Complete Analysis Suite - InfoCube & InfoObject Analysis with Full Capabilities")
        st.markdown("---")

        # Performance warning
        if st.session_state.data_loaded:
            total_objects = sum(len(objects) for objects in st.session_state.global_inventory.values())
            if total_objects > 10000:
                st.warning(f"⚠️ Large dataset detected ({total_objects:,} objects). All performance optimizations available.")

        # Sidebar for navigation and controls
        with st.sidebar:
            st.header("🎮 Complete Navigation & Controls")

            # Page selection - COMPLETE with all features
            page = st.selectbox(
                "📄 Select Analysis Page",
                ["🏠 Home & Data Loading",
                 "🧊 InfoCube Connection Analysis",
                 "🔍 InfoObject Impact Analysis",
                 "🎯 Advanced 3D Network Visualization",
                 "📊 Analytics Dashboard",
                 "🔍 Object Explorer",
                 "📋 Reports & Export"],
                help="Choose your analysis focus - all features available"
            )

            st.markdown("---")

            # Performance settings
            if st.session_state.data_loaded:
                st.subheader("⚡ Performance Settings")

                max_nodes = st.slider(
                    "Max nodes in 3D view",
                    min_value=100,
                    max_value=5000,
                    value=min(self.MAX_NODES_3D, sum(len(objects) for objects in st.session_state.global_inventory.values())),
                    step=100,
                    help="Reduce for better performance"
                )

                sampling_method = st.selectbox(
                    "Sampling Strategy",
                    ["Smart Sampling", "Random Sampling", "Top Connected", "By Priority"],
                    help="How to select objects for visualization"
                )

                st.session_state.max_nodes_3d = max_nodes
                st.session_state.sampling_method = sampling_method

                # Feature availability indicator
                total_objects = sum(len(objects) for objects in st.session_state.global_inventory.values())
                if total_objects > 20000:
                    st.info("🔥 **Large Dataset Mode**\nAll optimizations active")
                elif total_objects > 5000:
                    st.info("⚡ **Performance Mode**\nOptimizations available")
                else:
                    st.success("✅ **Full Feature Mode**\nAll capabilities enabled")

                st.markdown("---")

            # Data loading section
            st.subheader("📂 Data Source")

            upload_option = st.radio(
                "Choose data source:",
                ["📁 Upload Database File", "🗂️ Enter File Path"]
            )

            db_path = None
            if upload_option == "📁 Upload Database File":
                uploaded_file = st.file_uploader(
                    "Upload SQLite database file",
                    type=['db', 'sqlite', 'sqlite3'],
                    help="Upload your SAP BW metadata database file"
                )
                if uploaded_file:
                    with open("temp_database.db", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    db_path = "temp_database.db"
            else:
                db_path = st.text_input(
                    "Database file path:",
                    value="./SQLlite/lmy_database.db",
                    help="Enter the path to your database file"
                )

            # Load data button
            if st.button("🚀 Load & Analyze Data", type="primary"):
                if db_path:
                    with st.spinner("🔄 Loading and analyzing data for all features..."):
                        success = load_and_analyze_data(self, db_path)
                        if success:
                            st.success("✅ Data loaded successfully! All features ready.")
                            st.session_state.data_loaded = True
                            st.rerun()
                        else:
                            st.error("❌ Failed to load data")
                else:
                    st.error("Please provide a database path or upload a file")

            # Quick stats in sidebar
            if st.session_state.data_loaded:
                st.markdown("---")
                st.markdown("### 📊 Quick Stats")
                stats = st.session_state.dataset_stats
                st.write(f"📦 Objects: {stats.get('total_objects', 0):,}")
                st.write(f"🔗 Connections: {stats.get('total_relationships', 0):,}")

                cube_count = len(st.session_state.global_inventory.get('CUBE', []))
                iobj_count = len(st.session_state.global_inventory.get('IOBJ', []))
                ds_count = len(st.session_state.global_inventory.get('DS', []))

                st.write(f"🧊 InfoCubes: {cube_count:,}")
                st.write(f"🏷️ InfoObjects: {iobj_count:,}")
                st.write(f"📡 DataSources: {ds_count:,}")

        # Main content area based on selected page - ALL FEATURES AVAILABLE
        if page == "🏠 Home & Data Loading":
            show_home_page(self)
        elif page == "🧊 InfoCube Connection Analysis":
            show_infocube_connection_analysis(self)
        elif page == "🔍 InfoObject Impact Analysis":
            show_infoobject_impact_analysis(self)
        elif page == "🎯 Advanced 3D Network Visualization":
            show_optimized_3d_visualization_page(self)
        elif page == "📊 Analytics Dashboard":
            show_analytics_dashboard(self)
        elif page == "🔍 Object Explorer":
            show_object_explorer(self)
        elif page == "📋 Reports & Export":
            show_reports_page(self)


# Main application
def main():
    analyzer = SAP_BW_Enhanced_Analyzer()
    analyzer.create_main_interface()


if __name__ == "__main__":
    main()
