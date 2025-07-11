import pytest
from unittest.mock import patch, MagicMock
from frontend.app import SAP_BW_Enhanced_Analyzer

# 🔧 Clase auxiliar para simular correctamente st.session_state
class MockSessionState(dict):
    def __getattr__(self, item):
        return self[item] if item in self else None

    def __setattr__(self, key, value):
        self[key] = value

# ✅ Test 1: Verifica que __init__ inicializa correctamente el estado de sesión
@patch("frontend.app.st")
def test_init_sets_session_state_defaults(mock_st):
    mock_st.session_state = MockSessionState()

    analyzer = SAP_BW_Enhanced_Analyzer()

    assert mock_st.session_state.data_loaded is False
    assert isinstance(mock_st.session_state.global_inventory, dict)
    assert isinstance(mock_st.session_state.relationships, list)
    assert mock_st.session_state.graph is not None
    assert isinstance(mock_st.session_state.dataset_stats, dict)
    assert isinstance(mock_st.session_state.pos_3d, dict)


# ✅ Test 2: Verifica que se llama a la función de Home cuando se selecciona desde el sidebar
@patch("frontend.app.show_home_page")
@patch("frontend.app.st")
def test_home_page_rendering(mock_st, mock_show_home):
    mock_st.session_state = MockSessionState(
        data_loaded=False,
        global_inventory={},
        relationships=[],
        graph=MagicMock(),
        dataset_stats={},
        pos_3d={}
    )

    mock_st.selectbox.return_value = "🏠 Home & Data Loading"
    mock_st.sidebar = MagicMock()

    analyzer = SAP_BW_Enhanced_Analyzer()
    analyzer.create_main_interface()

    mock_show_home.assert_called_once_with(analyzer)


# ✅ Test 3: Verifica que se llama a la función de InfoCube cuando se selecciona desde el sidebar
@patch("frontend.app.show_infocube_connection_analysis")
@patch("frontend.app.st")
def test_infocube_page_rendering(mock_st, mock_show_cube):
    mock_st.session_state = MockSessionState(
        data_loaded=False,
        global_inventory={},
        relationships=[],
        graph=MagicMock(),
        dataset_stats={},
        pos_3d={}
    )

    mock_st.selectbox.return_value = "🧊 InfoCube Connection Analysis"
    mock_st.sidebar = MagicMock()

    analyzer = SAP_BW_Enhanced_Analyzer()
    analyzer.create_main_interface()

    mock_show_cube.assert_called_once_with(analyzer)
