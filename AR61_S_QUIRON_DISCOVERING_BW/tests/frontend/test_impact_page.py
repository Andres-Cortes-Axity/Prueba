import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from frontend.impact_page import show_infoobject_impact_analysis


@pytest.fixture
def mock_app():
    return type("MockApp", (), {})()


@patch("frontend.impact_page.analyze_infoobject_impact_with_sources")
@patch("frontend.impact_page.display_impact_analysis_with_sources")
@patch("frontend.impact_page.st")
def test_show_infoobject_impact_analysis_basic(mock_st, mock_display, mock_analyze, mock_app):
    # Mock session state
    mock_st.session_state = SimpleNamespace(
        data_loaded=True,
        global_inventory={"IOBJ": [{"name": "ZCUST"}]}
    )

    # Mock UI behavior
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    mock_st.text_input.return_value = ""
    mock_st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    mock_st.slider.return_value = 3
    mock_st.checkbox.side_effect = lambda label, value=True, help=None: value
    mock_st.multiselect.side_effect = lambda label, options, default, help=None: default
    mock_st.button.side_effect = [True, False]
    mock_st.spinner.return_value.__enter__.return_value = MagicMock()
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.info = MagicMock()
    mock_st.warning = MagicMock()

    # Mock results
    mock_analyze.return_value = {
        "connected_objects": {"DS": []},
        "relationships": [],
        "analysis_depth": 3
    }

    # Ejecuta
    show_infoobject_impact_analysis(mock_app)

    # Verifica que se haya analizado correctamente
    mock_analyze.assert_called_once()
    mock_display.assert_called_once()
