import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from frontend.infocube_page import show_infocube_connection_analysis


@pytest.fixture
def mock_app():
    return type("MockApp", (), {})()


@patch("frontend.infocube_page.analyze_infocube_connections")
@patch("frontend.infocube_page.st")
def test_show_infocube_connection_analysis_basic(mock_st, mock_analyze, mock_app):
    # Simula una InfoCube
    mock_st.session_state = SimpleNamespace(
        data_loaded=True,
        global_inventory={
            "CUBE": [
                {"name": "ZCUBE_TEST", "category": "Provider", "icon": "🧊"}
            ]
        }
    )

    # Simula la UI
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    mock_st.text_input.return_value = ""
    mock_st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    mock_st.slider.return_value = 3
    mock_st.checkbox.side_effect = lambda label, value=True, help=None: value
    mock_st.multiselect.side_effect = lambda label, options, default, help=None: default
    mock_st.button.side_effect = [True, False, False, False]  # Solo activa el primer botón
    mock_st.spinner.return_value.__enter__.return_value = MagicMock()
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.info = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.error = MagicMock()

    # Simula el resultado de análisis
    mock_analyze.return_value = {
        "total_objects": 5,
        "total_relationships": 4,
        "connected_objects": {"DS": [], "IOBJ": []},
        "relationships": [],
        "analysis_depth": 3,
        "data_lineage_paths": []
    }

    # Parcha display_infocube_connection_analysis para no ejecutarla
    with patch("frontend.infocube_page.display_infocube_connection_analysis"):
        show_infocube_connection_analysis(mock_app)

    # Validaciones
    mock_st.header.assert_called_once_with("🧊 InfoCube Connection Analysis with Complete Source Tracing")
    mock_analyze.assert_called_once()
