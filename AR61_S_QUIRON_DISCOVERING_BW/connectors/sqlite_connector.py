import streamlit as st
import sqlite3
from datetime import datetime
import networkx as nx

from backend.enhaced_relationships import get_active_objects_by_type
from backend.enhaced_relationships import analyze_enhanced_relationships
from backend.enhaced_relationships import build_relationship_graph


def load_and_analyze_data(self, db_path):
    """Load and analyze data with progress tracking"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)

        # Get available tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        available_tables = set(table[0] for table in cursor.fetchall())

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Load objects by type
        global_inventory = {}
        total_objects = 0

        for i, (obj_type, config) in enumerate(self.object_types.items()):
            status_text.text(f"Loading {config['name']}s...")
            progress_bar.progress((i + 1) / (len(self.object_types) + 2))

            if config['table'] in available_tables:
                objects = get_active_objects_by_type(self, conn, obj_type, config)
                global_inventory[obj_type] = objects
                total_objects += len(objects)
            else:
                global_inventory[obj_type] = []

        # Analyze relationships - Enhanced for InfoCube connections
        status_text.text("Analyzing relationships and source connections...")
        progress_bar.progress(0.9)
        relationships = analyze_enhanced_relationships(self, conn, available_tables)

        # Build graph
        status_text.text("Building network graph...")
        progress_bar.progress(0.95)
        graph = build_relationship_graph(self, global_inventory, relationships)

        # Store dataset statistics
        dataset_stats = {
            'total_objects': total_objects,
            'total_relationships': len(relationships),
            'object_type_counts': {obj_type: len(objects) for obj_type, objects in global_inventory.items()},
            'graph_density': nx.density(graph) if graph.nodes else 0,
            'load_timestamp': datetime.now().isoformat()
        }

        # Store in session state
        st.session_state.global_inventory = global_inventory
        st.session_state.relationships = relationships
        st.session_state.graph = graph
        st.session_state.dataset_stats = dataset_stats

        # Clear progress indicators
        progress_bar.progress(1.0)
        status_text.text("✅ Data loaded successfully!")

        conn.close()
        return True

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return False
