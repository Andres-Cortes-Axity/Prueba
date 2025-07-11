import pytest
import streamlit as st
from datetime import datetime

from connectors.source_detectors import get_source_system_info
from frontend.reports_page import show_reports_page

class DummyCol:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

@pytest.fixture(autouse=True)
def reset_session(monkeypatch):
    # Limpia session_state y garantiza data_loaded por defecto
    st.session_state.clear()
    st.session_state.data_loaded = False

    calls = {
        'warning': [],
        'text_area': [],
        'download_button': [],
        'spinner': [],
        'success': [],
        'markdown': []
    }

    # Stub de funciones de Streamlit para capturar llamadas
    monkeypatch.setattr(st, 'warning', lambda msg: calls['warning'].append(msg))
    monkeypatch.setattr(st, 'header', lambda msg: None)
    monkeypatch.setattr(st, 'subheader', lambda msg: None)
    monkeypatch.setattr(st, 'columns', lambda *args, **kwargs: (DummyCol(), DummyCol()))
    monkeypatch.setattr(st, 'button', lambda label: False)
    monkeypatch.setattr(st, 'text_area', lambda label, data, height=None: calls['text_area'].append((label, data)))
    monkeypatch.setattr(st, 'download_button', lambda **kwargs: calls['download_button'].append(kwargs))
    monkeypatch.setattr(st, 'spinner', lambda msg=None: DummyCol())
    monkeypatch.setattr(st, 'success', lambda msg: calls['success'].append(msg))
    monkeypatch.setattr(st, 'markdown', lambda md: calls['markdown'].append(md))

    return calls

def test_warning_when_not_loaded(reset_session):
    """Debe advertir si data_loaded es False y no proceder."""
    show_reports_page(None)
    assert reset_session['warning'] == ["⚠️ Please load data first from the Home page"]
    assert reset_session['text_area'] == []
    assert reset_session['download_button'] == []


def test_performance_tips_large_and_small(reset_session):
    """Muestra advertencia o éxito según total_objects."""
    st.session_state.data_loaded = True
    st.button = lambda lbl: False

    # Caso dataset grande
    st.session_state.dataset_stats = {'total_objects': 30000}
    show_reports_page(None)
    assert any("Large Dataset Optimization Tips" in msg for msg in reset_session['warning'])

    # Reiniciar y probar dataset pequeño
    reset_session['warning'].clear()
    reset_session['success'].clear()

    st.session_state.dataset_stats = {'total_objects': 100}
    show_reports_page(None)
    assert any("Your dataset size is manageable" in msg for msg in reset_session['success'])
