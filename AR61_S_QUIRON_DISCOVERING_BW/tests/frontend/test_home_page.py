from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from frontend.home_page import show_home_page


class MockApp:
    object_types = {
        "CUBE": {"icon": "🧊", "name": "InfoCube", "priority": 3},
        "IOBJ": {"icon": "🏷️", "name": "InfoObject", "priority": 2},
        "DS": {"icon": "📡", "name": "DataSource", "priority": 1},
    }


@patch("frontend.home_page.st")
def test_show_home_page_with_data(mock_st, mock_app=MockApp()):
    mock_st.session_state = SimpleNamespace(
        data_loaded=True,
        dataset_stats={"total_objects": 12000, "total_relationships": 34000},
        global_inventory={
            "CUBE": [{"name": "ZCUBE1"}, {"name": "ZCUBE2"}],
            "IOBJ": [{"name": "ZCUST"}],
            "DS": [{"name": "ZDS"}],
        }
    )

    mock_st.columns.side_effect = lambda spec: [MagicMock() for _ in range(len(spec))]
    mock_st.metric = MagicMock()
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.success = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.error = MagicMock()
    mock_st.info = MagicMock()
    mock_st.write = MagicMock()

    show_home_page(mock_app)


@patch("frontend.home_page.st")
def test_show_home_page_without_data(mock_st, mock_app=MockApp()):
    mock_st.session_state = SimpleNamespace(data_loaded=False)

    mock_st.columns.side_effect = lambda spec: [MagicMock() for _ in range(len(spec))]
    mock_st.header = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.info = MagicMock()

    show_home_page(mock_app)
