# tests/connectors/test_sqlite_connector.py

import sqlite3
import networkx as nx
import pytest
import streamlit as st

from frontend.app import SAP_BW_Enhanced_Analyzer
import connectors.sqlite_connector as sqlite_mod


class FakeCursor:
    def execute(self, query, *args, **kwargs):
        pass

    def fetchall(self):
        # Simulamos que existen dos tablas: T1 y T2
        return [("T1",), ("T2",)]


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


class FakeProgress:
    def __init__(self):
        self.values = []

    def progress(self, val):
        self.values.append(val)


class FakeStatus:
    def __init__(self):
        self.messages = []

    def text(self, msg):
        self.messages.append(msg)


def test_load_and_analyze_data_con_mocks(monkeypatch):
    # 1. Creamos la instancia y reducimos object_types a un subset controlado
    analyzer = SAP_BW_Enhanced_Analyzer()
    analyzer.object_types = {
        "A": {"name": "Tipo A", "table": "T1"},
        "B": {"name": "Tipo B", "table": "T2"},
        "C": {"name": "Tipo C", "table": "T3"},
    }

    # 2. Mock sqlite3.connect para devolver FakeConn
    fake_conn = FakeConn()
    monkeypatch.setattr(sqlite3, "connect", lambda path: fake_conn)

    # 3. Mock Streamlit UI (progress + status text)
    fake_prog = FakeProgress()
    monkeypatch.setattr(st, "progress", lambda initial: fake_prog)
    fake_stat = FakeStatus()
    monkeypatch.setattr(st, "empty", lambda: fake_stat)

    # 4. Mockeamos las funciones internas en el módulo sqlite_mod
    monkeypatch.setattr(
        sqlite_mod,
        "get_active_objects_by_type",
        lambda self, conn, obj_type, config: ["o1", "o2"],
    )
    monkeypatch.setattr(
        sqlite_mod,
        "analyze_enhanced_relationships",
        lambda self, conn, tables: ["r1", "r2"],
    )
    monkeypatch.setattr(
        sqlite_mod,
        "build_relationship_graph",
        lambda self, gi, rels: nx.Graph([("n1", "n2"), ("n2", "n3")]),
    )

    # 5. Llamamos directamente a la función importada
    resultado = sqlite_mod.load_and_analyze_data(analyzer, "ruta_inventada.db")
    assert resultado is True

    # 6. Verificamos session_state
    gi = st.session_state.global_inventory
    assert set(gi.keys()) == {"A", "B", "C"}
    assert gi["A"] == ["o1", "o2"]
    assert gi["B"] == ["o1", "o2"]
    assert gi["C"] == []  # "T3" no estaba en fake_cursor.fetchall()

    assert st.session_state.relationships == ["r1", "r2"]

    g = st.session_state.graph
    assert isinstance(g, nx.Graph)
    assert g.number_of_nodes() == 3  # n1, n2, n3

    stats = st.session_state.dataset_stats
    assert stats["total_objects"] == 4       # 2 + 2 + 0
    assert stats["total_relationships"] == 2  # len(["r1","r2"])
    assert stats["object_type_counts"] == {"A": 2, "B": 2, "C": 0}
    # Densidad según las aristas del fake_graph
    expected_density = nx.density(g)
    assert stats["graph_density"] == expected_density
    assert "load_timestamp" in stats         # marca de tiempo generada
