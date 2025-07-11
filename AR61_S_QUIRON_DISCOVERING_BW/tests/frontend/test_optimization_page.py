import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import streamlit as st
from frontend.optimization_page import show_optimized_3d_visualization_page


@pytest.fixture
def mock_app():
    return SimpleNamespace(
        object_types={
            "IOBJ": {"name": "InfoObject", "icon": "🏷️", "priority": 3},
            "DSO": {"name": "DataStore", "icon": "🗂️", "priority": 2},
        }
    )


@pytest.fixture(autouse=True)
def setup_session_state():
    st.session_state.data_loaded = True
    st.session_state.global_inventory = {
        "IOBJ": [{"name": "ZCUST", "infoarea": "SALES"}, {"name": "ZPROD", "infoarea": "PRODUCT"}],
        "DSO": [{"name": "DSO_1", "infoarea": "SALES"}]
    }
    st.session_state.relationships = list(range(3000))


@pytest.mark.parametrize("connected_pct, avg_conn, max_conn", [(85.0, 3.2, 10)])
@patch("frontend.optimization_page.calculate_connection_percentages")
@patch("frontend.optimization_page.st")
def test_basic_visualization_metrics(mock_st, mock_calc_conn_pct, mock_app, connected_pct, avg_conn, max_conn):
    # Simula el resultado de calculate_connection_percentages
    mock_calc_conn_pct.return_value = {
        "overall_connected_percentage": connected_pct,
        "average_connections": avg_conn,
        "max_connections": max_conn,
        "by_object_type": {
            "IOBJ": {"connected_percentage": 90.0},
            "DSO": {"connected_percentage": 70.0}
        }
    }

    # Devuelve el número correcto de columnas según el input
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]

    # Controles de Streamlit simulados
    mock_st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    mock_st.multiselect.side_effect = lambda label, options, **kwargs: options
    mock_st.slider.side_effect = lambda *args, **kwargs: kwargs.get("value", 100)
    mock_st.checkbox.return_value = True
    mock_st.number_input.return_value = 1
    mock_st.button.return_value = False  # El botón no se presiona
    mock_st.metric = MagicMock()
    mock_st.header = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.subheader = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.info = MagicMock()
    mock_st.error = MagicMock()

    # Ejecutar la función objetivo
    show_optimized_3d_visualization_page(mock_app)

    # Validaciones básicas
    mock_st.metric.assert_any_call("Connected %", f"{connected_pct:.1f}%")
    mock_st.metric.assert_any_call("Avg Connections", f"{avg_conn:.1f}")
    mock_st.metric.assert_any_call("Max Connections", f"{max_conn}")

    mock_st.selectbox.assert_any_call(
        "Choose visualization approach:",
        [
            "🎯 Smart Sample (Recommended)",
            "🔗 Connection-Based Sampling",
            "🔍 Filtered View",
            "📊 Category Focus",
            "🎲 Random Sample",
            "🔗 Most Connected Only",
            "🏷️ InfoObject Impact Focus"
        ],
        help="Different strategies for handling large datasets with connection analysis"
    )
