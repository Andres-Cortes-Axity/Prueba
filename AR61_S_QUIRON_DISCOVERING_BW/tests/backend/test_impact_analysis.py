# tests/backend/test_analyze_infoobject_impact.py

import sys
import os
import networkx as nx
import streamlit as st
import pytest
import importlib
from collections import OrderedDict
import datetime as real_datetime
from backend.impact_analysis import analyze_infoobject_impact_with_sources
from backend.impact_analysis import display_impact_analysis_with_sources
from backend.impact_analysis import create_impact_analysis_3d_visualization
from backend.impact_analysis import trace_to_data_sources
from backend.impact_analysis import calculate_impact_analysis_positions
from backend.impact_analysis import add_impact_analysis_edges
from backend.impact_analysis import prepare_impact_analysis_csv_with_sources
import backend.impact_analysis as ia_mod

# Aseguramos que el proyecto esté en sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def setup_graph():
    # Limpia sesión y crea un grafo vacío antes de cada test
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    yield
    st.session_state.clear()


def test_no_target_node():
    """
    Si el nodo objetivo no está en el grafo, debe devolver None.
    """
    result = analyze_infoobject_impact_with_sources(
        None,
        iobj_name="X",
        depth=1,
        include_source_tracing=False,
        connection_types=["any"],
        show_source_systems=False
    )
    assert result is None


# def test_simple_bfs_without_source_tracing():
#     """
#     Con depth=1 y tracing deshabilitado, debe encontrar relaciones
#     outgoing/incoming según connection_types y calcular stats.
#     """
#     g = st.session_state.graph
#     # Creamos nodos de prueba
#     g.add_node("IOBJ:T1", type="IOBJ", name="T1")
#     g.add_node("CUBE:C1", type="CUBE", name="C1")
#     # Conectamos IOBJ:T1 → CUBE:C1 con tipo 'usage'
#     g.add_edge("IOBJ:T1", "CUBE:C1", type="usage", weight=1)

#     result = analyze_infoobject_impact_with_sources(
#         None,
#         iobj_name="T1",
#         depth=1,
#         include_source_tracing=False,
#         connection_types=["usage"],
#         show_source_systems=False
#     )

#     # Validaciones generales
#     assert result["target_iobj"] == "T1"
#     assert result["analysis_depth"] == 1
#     assert result["source_tracing_enabled"] is False
#     assert result["total_objects"] == 1
#     assert result["total_relationships"] == 1
#     assert result["total_source_connections"] == 0

#     # Validamos connected_objects para tipo CUBE
#     assert "CUBE" in result["connected_objects"]
#     cube_objs = result["connected_objects"]["CUBE"]
#     assert len(cube_objs) == 1
#     obj = cube_objs[0]
#     assert obj["node_id"] == "CUBE:C1"
#     assert obj["type"] == "CUBE"
#     # Conexiones entrantes y salientes
#     assert obj["connections_out"] == 0
#     assert obj["connections_in"] == 1
#     assert obj["total_connections"] == 1

#     # Validamos relationships_found
#     rel = result["relationships"][0]
#     assert rel["source"] == "IOBJ:T1"
#     assert rel["target"] == "CUBE:C1"
#     assert rel["direction"] == "outgoing"
#     assert rel["depth"] == 1
#     assert rel["type"] == "usage"
#     assert rel["weight"] == 1


def test_with_source_tracing(monkeypatch):
    """
    Cuando include_source_tracing=True, debe invocar trace_to_data_sources,
    recoger source_connections y añadir nodos DS al análisis.
    Además, show_source_systems=True añade source_system al object_info.
    """
    g = st.session_state.graph
    # Nodo InfoObject y nodo DataSource
    g.add_node("IOBJ:T2", type="IOBJ", name="T2")
    g.add_node("DS:S1", type="DS", name="S1")

    # No hay aristas; simularemos tracing
    def fake_trace(self, node, depth):
        if node == "IOBJ:T2" and depth == 1:
            return [{
                "source_node": "DS:S1",
                "source": "IOBJ:T2",
                "target": "DS:S1",
                "type": "source_connection",
                "weight": 2
            }]
        return []

    monkeypatch.setattr(ia_mod, "trace_to_data_sources", fake_trace)
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, name: "SYS")

    result = analyze_infoobject_impact_with_sources(
        None,
        iobj_name="T2",
        depth=2,
        include_source_tracing=True,
        connection_types=[],          # no relaciones de graph
        show_source_systems=True
    )

    # Debe detectar una source_connection
    assert result["total_source_connections"] == 1
    # relationships sigue vacío
    assert result["total_relationships"] == 0

    # connected_objects debe incluir DS
    ds_list = result["connected_objects"].get("DS", [])
    assert len(ds_list) == 1
    ds_obj = ds_list[0]
    # Campos calculados correctamente
    assert ds_obj["node_id"] == "DS:S1"
    assert ds_obj["type"] == "DS"
    # Al mostrar sistemas, se añade source_system
    assert ds_obj["source_system"] == "SYS"

    # source_connections recoge el dict de fake_trace
    assert result["source_connections"][0]["source_node"] == "DS:S1"
    # depth y flags
    assert result["analysis_depth"] == 2
    assert result["source_tracing_enabled"] is True

# ---------------------------------------------------------------------------
# trace_to_data_sources
import backend.impact_analysis as ia_mod


@pytest.fixture(autouse=True)
def setup_graph():
    """Limpia session_state y crea un grafo vacío antes de cada test."""
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    yield
    st.session_state.clear()


def test_trace_no_connections():
    """
    Si no hay predecesores de tipo DS ni proveedores, debe devolver lista vacía.
    """
    st.session_state.graph.add_node("IOBJ:T3", type="IOBJ", name="T3")
    result = trace_to_data_sources(None, "IOBJ:T3", depth=3)
    assert result == []


def test_trace_direct_datasource(monkeypatch):
    """
    Debe detectar conexiones directas de DS al nodo, incluyendo tipo de edge y sistema.
    """
    # Creamos nodo DataSource y nodo objetivo
    st.session_state.graph.add_node("DS:D1", type="DS", name="N1")
    st.session_state.graph.add_node("IOBJ:T1", type="IOBJ", name="T1")
    # Añadimos la arista DS→IOBJ con tipo 'abc'
    st.session_state.graph.add_edge("DS:D1", "IOBJ:T1", type="abc")

    # Mockeamos sistema de origen
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, name: "SYS")

    result = trace_to_data_sources(None, "IOBJ:T1", depth=1)
    assert len(result) == 1

    entry = result[0]
    assert entry["source_node"] == "DS:D1"
    assert entry["target_node"] == "IOBJ:T1"
    assert entry["source_name"] == "N1"
    assert entry["source_type"] == "DataSource"
    assert entry["connection_type"] == "abc"
    assert entry["depth"] == 1
    assert entry["source_system"] == "SYS"


def test_trace_indirect_via_provider(monkeypatch):
    """
    Debe detectar conexiones DS→Proveedor→nodo, usando depth+1 y via_Provider.
    """
    # Creamos nodos: proveedor ADSO:P1, DS:D2, y nodo IOBJ:T2
    st.session_state.graph.add_node("ADSO:P1", type="ADSO", name="P1")
    st.session_state.graph.add_node("DS:D2", type="DS", name="D2")
    st.session_state.graph.add_node("IOBJ:T2", type="IOBJ", name="T2")
    # Aristas: DS:D2→ADSO:P1, ADSO:P1→IOBJ:T2
    st.session_state.graph.add_edge("DS:D2", "ADSO:P1", type="t1")
    st.session_state.graph.add_edge("ADSO:P1", "IOBJ:T2", type="t2")

    # Mockeamos sistema de origen
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, name: "SYS2")

    result = trace_to_data_sources(None, "IOBJ:T2", depth=1)
    assert len(result) == 1

    entry = result[0]
    assert entry["source_node"] == "DS:D2"
    assert entry["target_node"] == "IOBJ:T2"
    assert entry["intermediate_node"] == "ADSO:P1"
    assert entry["source_name"] == "D2"
    assert entry["source_type"] == "DataSource"
    assert entry["connection_type"] == "via_Provider"
    assert entry["depth"] == 2
    assert entry["source_system"] == "SYS2"

# ----------------------------------------------------------------------
# display_impact_analysis_with_sources


class DummyCol:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """
    Mockeamos las funciones de Streamlit para capturar llamadas.
    """
    calls = {
        'success': [], 'columns': [], 'metric': [],
        'info': [], 'warning': []
    }

    monkeypatch.setattr(st, "success", lambda msg: calls['success'].append(msg))
    monkeypatch.setattr(st, "columns", lambda n: calls['columns'].append(n) or [DummyCol() for _ in range(n)])
    monkeypatch.setattr(st, "metric", lambda label, value: calls['metric'].append((label, value)))
    monkeypatch.setattr(st, "info", lambda txt: calls['info'].append(txt))
    monkeypatch.setattr(st, "warning", lambda txt: calls['warning'].append(txt))
    # Otros métodos de Streamlit que no se usan en este escenario pueden omitirse
    return calls


@pytest.fixture(autouse=True)
def setup_graph():
    """
    Prepara un grafo vacío en session_state antes de cada test.
    """
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    yield
    st.session_state.clear()


def test_display_impact_analysis_empty_group(mock_streamlit):
    """
    Con group_by_type=True y sin datos, debe:
      - Mostrar métricas
      - Informar No upstream/downstream dependencies
      - Avisar No connected objects found
      - Retornar None
    """
    calls = mock_streamlit

    results = {
        'total_objects': 0,
        'total_relationships': 0,
        'total_source_connections': 0,
        'analysis_depth': 1,
        'source_connections': [],
        'relationships': [],
        'connected_objects': {}
    }

    ret = display_impact_analysis_with_sources(
        None,
        iobj_name="IOBJ1",
        results=results,
        group_by_type=True,
        show_details=False,
        render_3d=False
    )

    # 1) Métricas mostradas
    assert calls['success'] == ["✅ Impact Analysis with Source Tracing Complete!"]
    assert calls['columns'][0] == 5  # primeras columnas de métricas
    expected_metrics = [
        ("🎯 Target InfoObject", "IOBJ1"),
        ("🔗 Connected Objects", 0),
        ("↔️ Relationships", 0),
        ("📡 Source Connections", 0),
        ("🔍 Analysis Depth", 1),
    ]
    for em in expected_metrics:
        assert em in calls['metric']

    # 2) Mensajes de info por no dependencies
    assert any("No upstream dependencies found" in txt for txt in calls['info'])
    assert any("No downstream impact found" in txt for txt in calls['info'])

    # 3) Warning por no connected_objects
    assert calls['warning'] == ["No connected objects found"]

    # 4) Retorno None
    assert ret is None

# ---------------------------------------------------------------------------
# reate_impact_analysis_3d_visualization
import backend.impact_analysis as ia_mod


class FakeFig:
    def __init__(self):
        self.layout_kwargs = None

    def update_layout(self, **kwargs):
        # Guardamos los kwargs pasados para verificar luego
        self.layout_kwargs = kwargs


class FakeGo:
    Figure = FakeFig


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """
    Mock de las funciones de posicionamiento y de creación de edges/nodes,
    así como de go.Figure para aislar la lógica de ensamblaje.
    """
    calls = {}

    # Stub de posiciones 3D
    def fake_calc(self, graph, target_node):
        # Posiciones fijas para los nodos del grafo
        return {n: (i, i * 2, i * 3) for i, n in enumerate(graph.nodes)}

    monkeypatch.setattr(ia_mod, "calculate_impact_analysis_positions", fake_calc)

    # Stub para edges
    def fake_add_edges(self, fig, relationships, pos_3d):
        calls['edges'] = {
            'fig': fig,
            'relationships': relationships,
            'pos_3d': pos_3d.copy()
        }
    monkeypatch.setattr(ia_mod, "add_impact_analysis_edges", fake_add_edges)

    # Stub para nodes
    def fake_add_nodes(self, fig, objects, pos_3d, target_iobj):
        calls['nodes'] = {
            'fig': fig,
            'objects': objects.copy(),
            'pos_3d': pos_3d.copy(),
            'target_iobj': target_iobj
        }
    monkeypatch.setattr(ia_mod, "add_impact_analysis_nodes", fake_add_nodes)

    # Stub de plotly.go
    monkeypatch.setattr(ia_mod, "go", FakeGo)

    return calls


def test_returns_none_for_empty_objects():
    """
    Cuando la lista de objetos está vacía, debe retornar None.
    """
    fig = create_impact_analysis_3d_visualization(None, [], [], "X")
    assert fig is None


def test_builds_figure_and_calls_helpers(patch_dependencies):
    """
    Con objetos y relaciones válidas, debe:
      - Crear un grafo enfocado con los mismos nodos
      - Invocar calculate_impact_analysis_positions con el grafo y target
      - Crear la figura (FakeFig) y llamar a add_edges y add_nodes con los parámetros correctos
      - Configurar el título de la figura acorde al target
    """
    calls = patch_dependencies

    # Preparamos datos de entrada
    objects = [
        {'node_id': 'IOBJ:A', 'name': 'A', 'type': 'IOBJ'},
        {'node_id': 'CUBE:B', 'name': 'B', 'type': 'CUBE'},
    ]
    relationships = [
        {'source': 'IOBJ:A', 'target': 'CUBE:B', 'type': 't', 'weight': 1}
    ]
    target = "A"

    fig = create_impact_analysis_3d_visualization(None, objects, relationships, target)

    # Debe devolver instancia de FakeFig
    assert hasattr(fig, "layout_kwargs")

    # Verificamos que calculate posicionó ambos nodos
    # keys en pos_3d pasan a fake_add_edges y fake_add_nodes
    assert 'edges' in calls
    assert set(calls['edges']['pos_3d'].keys()) == {'IOBJ:A', 'CUBE:B'}
    assert calls['edges']['relationships'] == relationships

    # Verificamos que add_nodes recibió objetos y target
    assert 'nodes' in calls
    assert calls['nodes']['objects'] == objects
    assert calls['nodes']['target_iobj'] == target

    # Verificamos el título de la figura
    title_cfg = fig.layout_kwargs.get('title', {})
    assert isinstance(title_cfg, dict)
    assert title_cfg.get('text') == f'🎯 InfoObject Impact Analysis: {target}'

# --------------------------------------------------------------------------------
# calculate_impact_analysis_positions
import backend.impact_analysis as ia_mod


def test_returns_empty_when_target_not_in_graph():
    """
    Si el nodo objetivo no está en el grafo, debe devolver dict vacío.
    """
    g = nx.DiGraph()
    pos = calculate_impact_analysis_positions(None, g, "IOBJ:Z")
    assert pos == {}


def test_positions_called_and_positions_returned(monkeypatch):
    """
    Verifica que:
      - Se añada la posición central para el target.
      - Se invoque position_nodes_in_circle con los grupos upstream,
        downstream y other.
      - El diccionario pos_3d contenga las posiciones simuladas.
    """
    # Grafo de prueba
    g = nx.DiGraph()
    g.add_node("IOBJ:T", type="IOBJ")
    g.add_node("A", type="IOBJ")   # upstream
    g.add_node("B", type="IOBJ")   # downstream
    g.add_node("C", type="IOBJ")   # other

    g.add_edge("A", "IOBJ:T")      # A → target (upstream)
    g.add_edge("IOBJ:T", "B")      # target → B (downstream)
    # C no está conectado al target → other

    # Stub de position_nodes_in_circle
    calls = []

    def fake_position(self, nodes, pos_3d, center_z, radius, y_offset=0):
        calls.append({
            'nodes': list(nodes),
            'center_z': center_z,
            'radius': radius,
            'y_offset': y_offset
        })
        # Simula asignación de posición sencilla
        for i, node in enumerate(nodes):
            pos_3d[node] = {'x': i, 'y': y_offset, 'z': center_z}

    monkeypatch.setattr(ia_mod, "position_nodes_in_circle", fake_position)

    # Llamamos a la función
    pos = calculate_impact_analysis_positions(None, g, "IOBJ:T")

    # 1) Posición del target en el centro
    assert pos["IOBJ:T"] == {'x': 0, 'y': 0, 'z': 0}

    # 2) Se invocó position_nodes_in_circle tres veces
    assert len(calls) == 3

    # 3) Grupos y parámetros correctos
    # Upstream
    assert any(call['nodes'] == ["A"] and call['center_z'] == -3 and call['radius'] == 6 and call['y_offset'] == 0
               for call in calls)
    # Downstream
    assert any(call['nodes'] == ["B"] and call['center_z'] == 3 and call['radius'] == 6 and call['y_offset'] == 0
               for call in calls)
    # Other
    assert any(call['nodes'] == ["C"] and call['center_z'] == 0 and call['radius'] == 8 and call['y_offset'] == 8
               for call in calls)

    # 4) El diccionario pos incluye las posiciones simuladas
    assert pos["A"] == {'x': 0, 'y': 0, 'z': -3}
    assert pos["B"] == {'x': 0, 'y': 0, 'z': 3}
    assert pos["C"] == {'x': 0, 'y': 8, 'z': 0}

# ---------------------------------------------------------------------------------------
# create_impact_analysis_3d_visualization

import backend.impact_analysis as ia_mod


# Fakes para sustituir plotly.go y helpers internos
class FakeFig:
    def __init__(self):
        self.layout_kwargs = {}

    def update_layout(self, **kwargs):
        self.layout_kwargs.update(kwargs)


class FakeScatter3d:
    def __init__(self, **kwargs):
        pass


class FakeGo:
    Figure = FakeFig
    Scatter3d = FakeScatter3d


@pytest.fixture(autouse=True)

def patch_dependencies(monkeypatch):
    """
    Mockeamos:
      - calculate_impact_analysis_positions → devuelve posiciones fijas
      - add_impact_analysis_edges y add_impact_analysis_nodes → registran llamadas
      - go.Figure → FakeFig
    """
    calls = {}

    # Stub posiciones
    def fake_calc(self, graph, target_node):
        return {n: (i, i + 1, i + 2) for i, n in enumerate(graph.nodes)}

    monkeypatch.setattr(ia_mod, "calculate_impact_analysis_positions", fake_calc)

    # Stub edges
    def fake_edges(self, fig, relationships, pos_3d):
        calls['edges'] = {
            'relationships': relationships,
            'pos_3d': pos_3d.copy()
        }
    monkeypatch.setattr(ia_mod, "add_impact_analysis_edges", fake_edges)

    # Stub nodes
    def fake_nodes(self, fig, objects, pos_3d, target_iobj):
        calls['nodes'] = {
            'objects': objects.copy(),
            'pos_3d': pos_3d.copy(),
            'target_iobj': target_iobj
        }
    monkeypatch.setattr(ia_mod, "add_impact_analysis_nodes", fake_nodes)

    # Patch plotly
    monkeypatch.setattr(ia_mod, "go", FakeGo)

    return calls


def test_returns_none_for_empty_objects():
    """
    Cuando no hay objetos, debe retornar None.
    """
    fig = create_impact_analysis_3d_visualization(None, [], [], "X")
    assert fig is None


def test_builds_figure_and_updates_layout(patch_dependencies):
    """
    Con objetos y relaciones válidas, debe:
      - Llamar a calculate_impact_analysis_positions
      - Invocar add_edges y add_nodes
      - Actualizar el layout con el título correcto
      - Exponer layout_kwargs en el objeto retornado
    """
    calls = patch_dependencies

    objects = [
        {'node_id': 'IOBJ:A', 'name': 'A', 'type': 'IOBJ'},
        {'node_id': 'CUBE:B', 'name': 'B', 'type': 'CUBE'},
    ]
    relationships = [
        {'source': 'IOBJ:A', 'target': 'CUBE:B', 'type': 't', 'weight': 1}
    ]
    target = "A"

    fig = create_impact_analysis_3d_visualization(None, objects, relationships, target)

    # Verificamos que se hayan llamado los stubs de edges y nodes
    assert 'edges' in calls
    assert calls['edges']['relationships'] == relationships
    assert 'nodes' in calls
    assert calls['nodes']['objects'] == objects
    assert calls['nodes']['target_iobj'] == target

    # El objeto retornado debe exponer layout_kwargs con la configuración de título
    assert hasattr(fig, "layout_kwargs")
    title_cfg = fig.layout_kwargs.get('title', {})
    assert isinstance(title_cfg, dict)
    assert title_cfg.get('text') == f'🎯 InfoObject Impact Analysis: {target}'

# --------------------------------------------------------------------------
# calculate_impact_analysis_positions
import backend.impact_analysis as ia_mod


def test_returns_empty_when_target_not_in_graph():
    """
    Si el nodo objetivo no está en el grafo, debe devolver un dict vacío.
    """
    g = nx.DiGraph()
    pos = calculate_impact_analysis_positions(None, g, "IOBJ:X")
    assert pos == {}


def test_calls_position_nodes_in_circle_for_each_group(monkeypatch):
    """
    Verifica que, con un grafo que tenga nodos upstream, downstream y otros,
    se llame a position_nodes_in_circle tres veces con los parámetros correctos,
    y que las posiciones se añadan a pos_3d según lo que haga el stub.
    """
    # Construimos un grafo de ejemplo
    g = nx.DiGraph()
    g.add_node("IOBJ:T", type="IOBJ")
    g.add_node("A", type="IOBJ")   # upstream
    g.add_node("B", type="IOBJ")   # downstream
    g.add_node("C", type="IOBJ")   # other

    # Definimos aristas
    g.add_edge("A", "IOBJ:T")      # A → target = upstream
    g.add_edge("IOBJ:T", "B")      # target → B = downstream
    # C no conectado = other

    # Preparamos un stub para position_nodes_in_circle
    calls = []

    def fake_position(self, nodes, pos_3d, center_z, radius, y_offset=0):
        # Registramos la llamada
        calls.append({
            'nodes': list(nodes),
            'center_z': center_z,
            'radius': radius,
            'y_offset': y_offset
        })
        # Simulamos asignar posiciones en pos_3d
        for idx, node in enumerate(nodes):
            pos_3d[node] = {'x': idx, 'y': y_offset, 'z': center_z}

    monkeypatch.setattr(ia_mod, "position_nodes_in_circle", fake_position)

    # Ejecutamos la función bajo prueba
    pos = calculate_impact_analysis_positions(None, g, "IOBJ:T")

    # El target siempre en el centro
    assert pos["IOBJ:T"] == {'x': 0, 'y': 0, 'z': 0}

    # Debe llamarse tres veces
    assert len(calls) == 3

    # Verificamos cada grupo
    # Upstream: ["A"]
    assert any(call['nodes'] == ["A"] and call['center_z'] == -3 and call['radius'] == 6 and call['y_offset'] == 0
               for call in calls)
    # Downstream: ["B"]
    assert any(call['nodes'] == ["B"] and call['center_z'] == 3 and call['radius'] == 6 and call['y_offset'] == 0
               for call in calls)
    # Other: ["C"]
    assert any(call['nodes'] == ["C"] and call['center_z'] == 0 and call['radius'] == 8 and call['y_offset'] == 8
               for call in calls)

    # Además, las posiciones simuladas deben aparecer en pos
    assert pos["A"] == {'x': 0, 'y': 0, 'z': -3}
    assert pos["B"] == {'x': 0, 'y': 0, 'z': 3}
    assert pos["C"] == {'x': 0, 'y': 8, 'z': 0}

#-----------------------------------------------------------------------------------

# from backend.impact_analysis import add_impact_analysis_edges
# import backend.impact_analysis as ia_mod


# class FakeScatter3d:
#     def __init__(self, **kwargs):
#         # Guardamos todos los parámetros para poder inspeccionarlos
#         self.kwargs = kwargs


# class FakeGo:
#     Figure = FakeFig
#     Scatter3d = FakeScatter3d


# class FakeFig:
#     def __init__(self):
#         self.traces = []

#     def add_trace(self, trace):
#         self.traces.append(trace)


# @pytest.fixture(autouse=True)
# def patch_plotly(monkeypatch):
#     """
#     Parchea el alias 'go' dentro de backend.impact_analysis
#     para que use nuestro FakeGo con Scatter3d.
#     """
#     monkeypatch.setattr(ia_mod, "go", FakeGo)


# def test_add_impact_analysis_edges_both_directions():
#     """
#     Con relaciones 'incoming' y 'outgoing', debe crear dos trazas:
#       - Una upstream (verde) para los 'incoming'
#       - Una downstream (roja) para los 'outgoing'
#     """
#     fig = FakeFig()

#     pos_3d = {
#         "A": {"x": 0, "y": 0, "z": 0},
#         "B": {"x": 1, "y": 2, "z": 3},
#         "C": {"x": 4, "y": 5, "z": 6},
#     }
#     relationships = [
#         {"source": "A", "target": "B", "direction": "incoming"},
#         {"source": "B", "target": "C", "direction": "outgoing"},
#     ]

#     add_impact_analysis_edges(None, fig, relationships, pos_3d)

#     # Debe haber dos trazas: upstream y downstream
#     assert len(fig.traces) == 2

#     up, down = fig.traces

#     # Verificamos la traza upstream (A→B)
#     assert up.kwargs["x"] == [0, 1, None]
#     assert up.kwargs["y"] == [0, 2, None]
#     assert up.kwargs["z"] == [0, 3, None]
#     assert up.kwargs["line"]["color"] == "#00FF7F"
#     assert "Upstream (1)" in up.kwargs["name"]

#     # Verificamos la traza downstream (B→C)
#     assert down.kwargs["x"] == [1, 4, None]
#     assert down.kwargs["y"] == [2, 5, None]
#     assert down.kwargs["z"] == [3, 6, None]
#     assert down.kwargs["line"]["color"] == "#FF6347"
#     assert "Downstream (1)" in down.kwargs["name"]


# def test_add_impact_analysis_edges_ignores_missing_nodes():
#     """
#     Si una relación apunta a un nodo no presente en pos_3d,
#     no debe generar ninguna traza.
#     """
#     fig = FakeFig()

#     # Sólo 'A' existe
#     pos_3d = {"A": {"x": 0, "y": 0, "z": 0}}
#     # Relación A→B (B no existe)
#     relationships = [{"source": "A", "target": "B", "direction": "incoming"}]

#     add_impact_analysis_edges(None, fig, relationships, pos_3d)

#     # No se deben añadir trazas
#     assert fig.traces == []

# -------------------------------------------------------------------------------
# dd_impact_analysis_edges

import backend.impact_analysis as ia_mod


class FakeScatter3d:
    def __init__(self, **kwargs):
        # Guardamos los parámetros para luego inspeccionarlos
        self.kwargs = kwargs


class FakeGo:
    Figure = FakeFig
    # Solo necesitamos Scatter3d para esta función
    Scatter3d = FakeScatter3d


class FakeFig:
    def __init__(self):
        self.traces = []

    def add_trace(self, trace):
        self.traces.append(trace)


@pytest.fixture(autouse=True)
def patch_plotly(monkeypatch):
    """
    Parchea el alias 'go' dentro de backend.impact_analysis
    para que add_impact_analysis_edges use nuestro FakeScatter3d.
    """
    monkeypatch.setattr(ia_mod, "go", FakeGo)


def test_add_impact_analysis_edges_both_directions():
    """
    Con relaciones 'incoming' y 'outgoing', debe crear dos trazas:
      - Una upstream (verde) para los 'incoming'
      - Una downstream (roja) para los 'outgoing'
    """
    fig = FakeFig()

    pos_3d = {
        "A": {"x": 0, "y": 0, "z": 0},
        "B": {"x": 1, "y": 2, "z": 3},
        "C": {"x": 4, "y": 5, "z": 6},
    }
    relationships = [
        {"source": "A", "target": "B", "direction": "incoming"},
        {"source": "B", "target": "C", "direction": "outgoing"},
    ]

    add_impact_analysis_edges(None, fig, relationships, pos_3d)

    # Debe haber dos trazas: upstream y downstream
    assert len(fig.traces) == 2

    up, down = fig.traces

    # Verificamos la traza upstream (A→B)
    assert up.kwargs["x"] == [0, 1, None]
    assert up.kwargs["y"] == [0, 2, None]
    assert up.kwargs["z"] == [0, 3, None]
    assert up.kwargs["line"]["color"] == "#00FF7F"
    assert "Upstream (1)" in up.kwargs["name"]

    # Verificamos la traza downstream (B→C)
    assert down.kwargs["x"] == [1, 4, None]
    assert down.kwargs["y"] == [2, 5, None]
    assert down.kwargs["z"] == [3, 6, None]
    assert down.kwargs["line"]["color"] == "#FF6347"
    assert "Downstream (1)" in down.kwargs["name"]


def test_add_impact_analysis_edges_ignores_missing_nodes():
    """
    Si una relación apunta a un nodo no presente en pos_3d,
    no debe generar ninguna traza.
    """
    fig = FakeFig()
    pos_3d = {"A": {"x": 0, "y": 0, "z": 0}}
    relationships = [{"source": "A", "target": "B", "direction": "incoming"}]

    add_impact_analysis_edges(None, fig, relationships, pos_3d)

    # No se deben añadir trazas
    assert fig.traces == []

# ---------------------------------------------------------------------------------------
# prepare_impact_analysis_csv_with_sources
import backend.impact_analysis as ia_mod


@pytest.fixture(autouse=True)
def patch_datetime(monkeypatch):
    """
    Parchea ia_mod.datetime para devolver siempre una fecha fija.
    """
    class FakeDateTime:
        @classmethod
        def now(cls):
            # Retornamos un datetime real para que .strftime funcione
            return real_datetime.datetime(2025, 1, 2, 3, 4, 5)
    # Reload módulo para limpiar posibles parches previos
    importlib.reload(ia_mod)
    monkeypatch.setattr(ia_mod, "datetime", FakeDateTime)


def test_minimal_results():
    """
    Sin source_connections, connected_objects ni relationships,
    debe producir sólo las secciones de encabezado, Connected Objects y Relationships vacías.
    """
    results = {
        'target_iobj': 'T1',
        'total_objects': 0,
        'total_relationships': 0,
        'total_source_connections': 0,
        'analysis_depth': 1,
        'source_connections': [],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_impact_analysis_csv_with_sources(None, results)
    lines = csv.splitlines()

    # Encabezado
    assert lines[0] == "InfoObject Impact Analysis Report with Source Connections"
    assert lines[1] == "Target InfoObject,T1"
    assert lines[2] == "Analysis Date,2025-01-02 03:04:05"
    assert lines[3] == "Total Connected Objects,0"
    assert lines[4] == "Total Relationships,0"
    assert lines[5] == "Total Source Connections,0"
    assert lines[6] == "Analysis Depth,1"

    # Sección vacía y Connected Objects
    assert lines[7] == ""
    assert lines[8] == "Connected Objects"
    assert lines[9].startswith("Object Name,Object Type,Category,Owner")

    # Después del header de Connected Objects, no hay filas de datos
    # así que inmediatamente debe venir línea en blanco y luego Relationships
    assert lines[10] == ""
    assert lines[11] == "Relationships"
    assert lines[12] == "Source Object,Target Object,Connection Type,Direction,Depth"


def test_with_source_connections():
    """
    Con source_connections, debe incluir la sección Source Connections antes de Connected Objects.
    """
    results = {
        'target_iobj': 'T2',
        'total_objects': 0,
        'total_relationships': 0,
        'total_source_connections': 1,
        'analysis_depth': 2,
        'source_connections': [
            {
                'source_name': 'SRC',
                'source_system': 'SYS',
                'connection_type': 'ct',
                'depth': 3
            }
        ],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_impact_analysis_csv_with_sources(None, results)
    lines = csv.splitlines()

    # Encuentra la sección de Source Connections en la posición correcta
    idx = lines.index("Source Connections")
    assert lines[idx + 1] == "DataSource Name,Source System,Connection Type,Depth,Intermediate Object"
    # La fila de datos usa 'Direct' al no haber intermediate_node
    assert lines[idx + 2] == "SRC,SYS,ct,3,Direct"


def test_with_intermediate_source_connections():
    """
    Cuando source_connections contiene 'intermediate_node', el campo se extrae tras ':'.
    """
    results = {
        'target_iobj': 'T3',
        'total_objects': 0,
        'total_relationships': 0,
        'total_source_connections': 1,
        'analysis_depth': 1,
        'source_connections': [
            {
                'source_name': 'SRC2',
                'source_system': 'SYS2',
                'connection_type': 'ct2',
                'depth': 4,
                'intermediate_node': 'ADSO:P1'
            }
        ],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_impact_analysis_csv_with_sources(None, results)
    lines = csv.splitlines()

    idx = lines.index("Source Connections")
    # El intermediate_node 'ADSO:P1' debe convertirse en 'P1'
    assert lines[idx + 2].endswith(",P1")


def test_with_connected_objects_and_relationships():
    """
    Con connected_objects (DS y CUBE) y relationships,
    debe listar ambos objetos y relacionarlos correctamente.
    """
    results = {
        'target_iobj': 'T4',
        'total_objects': 2,
        'total_relationships': 1,
        'total_source_connections': 0,
        'analysis_depth': 3,
        'source_connections': [],
        'connected_objects': OrderedDict([
            ('DS', [
                {
                    'name': 'DS1',
                    'type_name': 'DataSource',
                    'category': 'Cat',
                    'owner': 'O',
                    'infoarea': 'IA',
                    'connections_in': 1,
                    'connections_out': 2,
                    'total_connections': 3,
                    'source_system': 'SYSX'
                }
            ]),
            ('CUBE', [
                {
                    'name': 'CB1',
                    'type_name': 'CubeName',
                    'category': 'CatC',
                    'owner': 'O2',
                    'infoarea': 'IA2',
                    'connections_in': 0,
                    'connections_out': 1,
                    'total_connections': 1
                    # no source_system for CUBE
                }
            ])
        ]),
        'relationships': [
            {
                'source': 'IOBJ:A',
                'target': 'CUBE:B',
                'type': 't',
                'direction': 'incoming',
                'depth': 5
            }
        ]
    }

    csv = prepare_impact_analysis_csv_with_sources(None, results)
    lines = csv.splitlines()

    # Sección Connected Objects
    idx_co = lines.index("Connected Objects")
    header_co = lines[idx_co + 1]
    assert header_co.startswith("Object Name,Object Type,Category,Owner")

    row_ds = lines[idx_co + 2].split(",")
    assert row_ds[0] == "DS1"
    assert row_ds[1] == "DataSource"
    assert row_ds[-1] == "SYSX"  # Columna Source System

    row_cube = lines[idx_co + 3].split(",")
    assert row_cube[0] == "CB1"
    assert row_cube[-1] == ""  # Para CUBE debe quedar vacío

    # Sección Relationships
    idx_rel = lines.index("Relationships")
    row_rel = lines[idx_rel + 2].split(",")
    assert row_rel == ["A", "B", "t", "incoming", "5"]
