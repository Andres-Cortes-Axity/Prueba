import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from frontend.object_explorer import show_object_explorer


@pytest.fixture
def mock_app():
    return type("MockApp", (), {
        "object_types": {
            "IOBJ": {"name": "InfoObject", "icon": "🏷️", "priority": 3},
            "DSO": {"name": "DataStore", "icon": "🗂️", "priority": 2},
        }
    })()


@patch("frontend.object_explorer.calculate_connection_percentages")
@patch("frontend.object_explorer.st")
def test_show_object_explorer_initial(mock_st, mock_connection_stats, mock_app):
    # Simula los datos de conexiones
    mock_connection_stats.return_value = {
        "overall_connected_percentage": 80.0,
        "isolated_percentage": 20.0,
        "average_connections": 3.5,
        "by_object_type": {
            "IOBJ": {"connected_percentage": 90.0, "average_connections": 4.0, "total": 2},
            "DSO": {"connected_percentage": 70.0, "average_connections": 3.0, "total": 1}
        }
    }

    # Simula streamlit UI
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    mock_st.selectbox.side_effect = lambda *args, **kwargs: kwargs.get("options", [])[0]
    mock_st.text_input.side_effect = lambda *args, **kwargs: ""
    mock_st.multiselect.side_effect = lambda *args, **kwargs: []
    mock_st.checkbox.return_value = True
    mock_st.slider.side_effect = lambda *args, **kwargs: kwargs.get("value", 1000)
    mock_st.number_input.side_effect = lambda *args, **kwargs: kwargs.get("value", 0)
    mock_st.button.return_value = False
    mock_st.metric = MagicMock()
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.info = MagicMock()
    mock_st.success = MagicMock()
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.write = MagicMock()
    mock_st.plotly_chart = MagicMock()
    mock_st.download_button = MagicMock()
    mock_st.spinner.return_value.__enter__.return_value = MagicMock()

    # ✅ Corrige: objetos deben ser dicts con keys esperadas
    mock_st.session_state = SimpleNamespace(
        dataset_stats={"total_objects": 2500},
        data_loaded=True,
        global_inventory={
            "IOBJ": [
                {"name": "OBJ1", "icon": "🏷️", "category": "Metadata", "infoarea": "INFO1", "owner": "USER1"},
                {"name": "OBJ2", "icon": "🏷️", "category": "Provider", "infoarea": "INFO2", "owner": "USER2"},
            ],
            "DSO": [
                {"name": "DSO1", "icon": "🗂️", "category": "Source", "infoarea": "INFO1", "owner": "USER3"},
            ]
        },
        graph=MagicMock()
    )

    # Fake graph degrees
    mock_st.session_state.graph.degree.side_effect = lambda node_id: {
        "IOBJ:OBJ1": 3,
        "IOBJ:OBJ2": 2,
        "DSO:DSO1": 4
    }.get(node_id, 0)

    # Ejecuta
    show_object_explorer(mock_app)

    # Validación básica
    mock_st.metric.assert_any_call("Total Objects", "2,500")
    mock_st.metric.assert_any_call("Connected Objects", "80.0%")
    mock_st.metric.assert_any_call("Isolated Objects", "20.0%")
