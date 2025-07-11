import streamlit as st
import networkx as nx


def analyze_enhanced_relationships(self, conn, available_tables):
    """Enhanced relationship analysis with better InfoCube and InfoSource support"""
    relationships = []

    try:
        cursor = conn.cursor()

        # Transformation relationships (enhanced)
        if 'RSTRAN' in available_tables:
            cursor.execute("""
                SELECT DISTINCT SOURCETYPE, SOURCENAME, TARGETTYPE, TARGETNAME, TRANID
                FROM RSTRAN
                WHERE OBJVERS = 'A' AND SOURCENAME IS NOT NULL AND TARGETNAME IS NOT NULL
                ORDER BY TRANID
            """)

            for row in cursor.fetchall():
                source_type, source_name, target_type, target_name, trans_id = row

                source_type_mapped = map_sap_type_to_our_type(self, source_type)
                target_type_mapped = map_sap_type_to_our_type(self, target_type)

                if source_type_mapped and target_type_mapped:
                    relationships.append({
                        'source': f"{source_type_mapped}:{source_name.strip()}",
                        'target': f"{target_type_mapped}:{target_name.strip()}",
                        'type': 'transformation',
                        'trans_id': trans_id,
                        'source_type': source_type_mapped,
                        'target_type': target_type_mapped,
                        'source_name': source_name.strip(),
                        'target_name': target_name.strip(),
                        'weight': 3,
                        'color': '#2E86C1'
                    })

        # InfoObject usage in InfoCubes (dimensions)
        if 'RSDDIMEIOBJ' in available_tables:
            cursor.execute("""
                SELECT DISTINCT IOBJNM, INFOCUBE
                FROM RSDDIMEIOBJ
                WHERE OBJVERS = 'A'
                LIMIT 20000
            """)

            for iobj_name, cube_name in cursor.fetchall():
                relationships.append({
                    'source': f"IOBJ:{iobj_name.strip()}",
                    'target': f"CUBE:{cube_name.strip()}",
                    'type': 'usage_dimension',
                    'source_type': 'IOBJ',
                    'target_type': 'CUBE',
                    'source_name': iobj_name.strip(),
                    'target_name': cube_name.strip(),
                    'weight': 2,
                    'color': '#E67E22'
                })

        # InfoObject usage in InfoCubes (key figures)
        if 'RSDCUBEIOBJ' in available_tables:
            cursor.execute("""
                SELECT DISTINCT IOBJNM, INFOCUBE
                FROM RSDCUBEIOBJ
                WHERE OBJVERS = 'A' AND IOBJTP = 'KYF'
                LIMIT 15000
            """)

            for iobj_name, cube_name in cursor.fetchall():
                relationships.append({
                    'source': f"IOBJ:{iobj_name.strip()}",
                    'target': f"CUBE:{cube_name.strip()}",
                    'type': 'usage_keyfigure',
                    'source_type': 'IOBJ',
                    'target_type': 'CUBE',
                    'source_name': iobj_name.strip(),
                    'target_name': cube_name.strip(),
                    'weight': 2,
                    'color': '#8E44AD'
                })

        # Enhanced DataSource connections
        if 'RSSELDONE' in available_tables:
            cursor.execute("""
                SELECT DISTINCT DS_NAME, IOBJNM
                FROM RSSELDONE
                WHERE OBJVERS = 'A' AND DS_NAME IS NOT NULL AND IOBJNM IS NOT NULL
                LIMIT 15000
            """)

            for ds_name, iobj_name in cursor.fetchall():
                relationships.append({
                    'source': f"DS:{ds_name.strip()}",
                    'target': f"IOBJ:{iobj_name.strip()}",
                    'type': 'source_connection',
                    'source_type': 'DS',
                    'target_type': 'IOBJ',
                    'source_name': ds_name.strip(),
                    'target_name': iobj_name.strip(),
                    'weight': 2,
                    'color': '#3498DB'
                })

        # Direct DataSource to InfoCube connections (if available)
        if 'RSDCUBEISOURCE' in available_tables:
            cursor.execute("""
                SELECT DISTINCT ISOURCE, INFOCUBE
                FROM RSDCUBEISOURCE
                WHERE OBJVERS = 'A'
                LIMIT 10000
            """)

            for isource_name, cube_name in cursor.fetchall():
                relationships.append({
                    'source': f"DS:{isource_name.strip()}",
                    'target': f"CUBE:{cube_name.strip()}",
                    'type': 'source_connection',
                    'source_type': 'DS',
                    'target_type': 'CUBE',
                    'source_name': isource_name.strip(),
                    'target_name': cube_name.strip(),
                    'weight': 3,
                    'color': '#16A085'
                })

    except Exception as e:
        st.error(f"Error analyzing enhanced relationships: {str(e)}")

    return relationships


def map_sap_type_to_our_type(self, sap_type):
    """Enhanced mapping with InfoSource support"""
    type_mapping = {
        'CUBE': 'CUBE', 'MPRO': 'CUBE', 'ADSO': 'ADSO',
        'ODSO': 'ODSO', 'DS': 'DS', 'IOBJ': 'IOBJ',
        'DATASOURCE': 'DS', 'ISOURCE': 'DS', 'RSDS': 'DS',
        'INFOSOURCE': 'DS', 'ROOSOURCE': 'DS'
    }
    return type_mapping.get(sap_type)


def get_active_objects_by_type(self, conn, object_type, config):
    """Get active objects for a specific type with error handling"""
    try:
        cursor = conn.cursor()
        table = config['table']
        key_field = config['key_field']

        # Get table structure
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]

        # Build query
        base_columns = [key_field]
        optional_columns = ['OBJVERS', 'OWNER', 'INFOAREA', 'ACTIVFL', 'OBJSTAT', 'CONTTIMESTMP']

        for col in optional_columns:
            if col in columns:
                base_columns.append(col)

        objvers_condition = "WHERE OBJVERS = 'A'" if 'OBJVERS' in columns else ""

        if object_type == 'CUBE' and 'CUBETYPE' in columns:
            if objvers_condition:
                objvers_condition += " AND (CUBETYPE != 'M' OR CUBETYPE IS NULL)"
            else:
                objvers_condition = "WHERE (CUBETYPE != 'M' OR CUBETYPE IS NULL)"

        query = f"""
            SELECT {', '.join(base_columns)}
            FROM {table}
            {objvers_condition}
            ORDER BY {key_field}
        """

        cursor.execute(query)
        results = cursor.fetchall()

        # Process results
        objects = []
        for row in results:
            obj = {
                'name': row[0],
                'type': object_type,
                'type_name': config['name'],
                'category': config['category'],
                'color': config['color'],
                'shape': config['shape'],
                'size_base': config['size_base'],
                'icon': config['icon'],
                'z_layer': config['z_layer']
            }

            # Add optional fields with defaults
            for i, col in enumerate(base_columns[1:], 1):
                if i < len(row) and row[i] is not None:
                    if col == 'OWNER':
                        obj['owner'] = row[i]
                    elif col == 'INFOAREA':
                        obj['infoarea'] = row[i]
                    elif col == 'ACTIVFL':
                        obj['active'] = 'Yes' if row[i] == 'X' else 'No'
                    elif col == 'OBJSTAT':
                        obj['status'] = row[i]
                    elif col == 'CONTTIMESTMP':
                        obj['last_changed'] = str(row[i])

            # Set defaults
            obj.setdefault('owner', 'Unknown')
            obj.setdefault('infoarea', 'UNASSIGNED')
            obj.setdefault('active', 'Unknown')
            obj.setdefault('status', 'Unknown')
            obj.setdefault('last_changed', 'Unknown')

            objects.append(obj)

        return objects

    except Exception as e:
        st.error(f"Error getting {object_type} objects: {str(e)}")
        return []


def build_relationship_graph(self, global_inventory, relationships):
    """Build NetworkX graph from relationships"""
    graph = nx.DiGraph()

    # Add nodes
    for obj_type, objects in global_inventory.items():
        for obj in objects:
            node_id = f"{obj_type}:{obj['name']}"
            graph.add_node(node_id, **obj)

    # Add edges (limit for performance)
    max_edges = 75000  # Increased for InfoCube analysis
    for i, rel in enumerate(relationships):
        if i >= max_edges:
            break
        if rel['source'] in graph.nodes and rel['target'] in graph.nodes:
            graph.add_edge(rel['source'], rel['target'], **rel)

    return graph
