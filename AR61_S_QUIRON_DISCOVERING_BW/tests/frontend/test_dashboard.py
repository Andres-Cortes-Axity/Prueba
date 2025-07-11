import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from frontend.dashboard import show_analytics_dashboard  # Asegúrate de usar la ruta correcta


class MockApp:
    object_types = {
        'CUBE': {'name': 'InfoCube', 'icon': '🧊', 'color': '#1f77b4', 'category': 'Data', 'priority': 3},
        'DS': {'name': 'DataSource', 'icon': '📡', 'color': '#2ca02c', 'category': 'Source', 'priority': 2},
        'IOBJ': {'name': 'InfoObject', 'icon': '🏷️', 'color': '#d62728', 'category': 'Field', 'priority': 1}
    }


@patch("frontend.dashboard.get_source_system_info", return_value="ECC")
@patch("frontend.dashboard.calculate_connection_percentages")
@patch("frontend.dashboard.st")
def test_show_analytics_dashboard(mock_st, mock_calc_conn, mock_get_source):
    # Simula session_state
    mock_st.session_state = SimpleNamespace(
        data_loaded=True,
        dataset_stats={
            'total_objects': 1000,
            'total_relationships': 500,
            'graph_density': 0.0123,
            'object_type_counts': {
                'CUBE': 10,
                'DS': 20,
                'IOBJ': 30
            }
        },
        global_inventory={
            'CUBE': [{'name': 'ZCUBE1', 'type_name': 'InfoCube'}],
            'DS': [{'name': 'ZDS1', 'type_name': 'DataSource'}],
            'IOBJ': [{'name': 'ZIOBJ1', 'type_name': 'InfoObject'}]
        },
        relationships=[
            {'type': 'uses'}, {'type': 'depends_on'}, {'type': 'uses'}
        ],
        graph=MagicMock()
    )

    mock_graph = mock_st.session_state.graph
    mock_graph.nodes = {'CUBE:ZCUBE1', 'DS:ZDS1', 'IOBJ:ZIOBJ1'}
    mock_graph.degree.side_effect = lambda node: {
        'CUBE:ZCUBE1': 5,
        'DS:ZDS1': 3,
        'IOBJ:ZIOBJ1': 2
    }.get(node, 0)

    # Simula salida de cálculo de porcentajes
    mock_calc_conn.return_value = {
        'overall_connected_percentage': 85.0,
        'isolated_percentage': 15.0,
        'connected_objects': 850,
        'isolated_objects': 150,
        'total_objects': 1000,
        'average_connections': 4.2,
        'max_connections': 12,
        'connection_level_distribution': {
            '0': 150,
            '1-5': 500,
            '6-10': 300,
            '10+': 50
        },
        'by_object_type': {
            'CUBE': {'connected_percentage': 90.0, 'average_connections': 5.5, 'total': 10, 'connected': 9},
            'DS': {'connected_percentage': 80.0, 'average_connections': 4.5, 'total': 20, 'connected': 16}
        },
        'most_connected_object': {
            'name': 'ZCUBE1',
            'type': 'InfoCube',
            'connections': 12
        }
    }

    # Simula componentes de Streamlit
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    mock_st.metric = MagicMock()
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.subheader = MagicMock()
    mock_st.plotly_chart = MagicMock()
    mock_st.dataframe = MagicMock()
    mock_st.write = MagicMock()
    mock_st.success = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.info = MagicMock()
    mock_st.error = MagicMock()
    mock_st.button.return_value = False
    mock_st.expander.return_value.__enter__.return_value = MagicMock()

    # Ejecuta la función
    show_analytics_dashboard(MockApp())
