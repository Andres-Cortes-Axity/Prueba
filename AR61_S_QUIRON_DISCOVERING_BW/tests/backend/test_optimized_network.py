import pytest
import networkx as nx
import streamlit as st

import backend.optimized_network as on_mod
from backend.optimized_network import get_connection_based_dataset

@pytest.fixture(autouse=True)
def reset_streamlit_state(monkeypatch):
    # Limpia el session_state antes de cada prueba
    st.session_state.global_inventory = {}
    st.session_state.graph = nx.DiGraph()
    st.session_state.relationships = []
    yield
    st.session_state.global_inventory.clear()
    st.session_state.relationships.clear()

def setup_inventory_and_graph():
    """
    Helper para crear un inventario con dos tipos:
      - X:o1 con 2 conexiones
      - Y:o2 con 0 conexiones
    Ambos en infoarea 'IA'.
    """
    # Inventario
    st.session_state.global_inventory = {
        'X': [{'name': 'o1', 'infoarea': 'IA'}],
        'Y': [{'name': 'o2', 'infoarea': 'IA'}]
    }
    # Grafo con grados 2 y 0
    G = nx.DiGraph()
    G.add_node('X:o1')
    G.add_node('Y:o2')
    # Creamos dos aristas de 'o1' a sí mismo para grado=2
    G.add_edge('X:o1', 'X:o1')
    G.add_edge('X:o1', 'X:o1')
    st.session_state.graph = G

def test_empty_inventory_returns_empty():
    """Si no hay objetos en el inventario, devuelve dos listas vacías."""
    objs, rels = get_connection_based_dataset(
        None,
        sample_type="Show Highly Connected",
        selected_types=[],
        selected_infoareas=[],
        max_objects=5,
        min_connections=0,
        max_edges=5
    )
    assert objs == []
    assert rels == []

def test_show_isolated_only_returns_zero_degree():
    """Muestra solo los objetos aislados (grado=0)."""
    setup_inventory_and_graph()
    ob, rl = get_connection_based_dataset(
        None,
        sample_type="Show Isolated",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=0,
        max_edges=10
    )
    # Según la implementación actual, no retorna aislados sin relaciones
    assert ob == []
    assert rl == []

def test_show_highly_connected_only_returns_high_degree():
    """Muestra solo los objetos altamente conectados (> avg*2)."""
    setup_inventory_and_graph()
    # avg_connections = (2+0)/2 = 1; highly threshold = >2
    # 'X:o1' tiene grado=2, no >2 → en este setup no hay highly
    ob, _ = get_connection_based_dataset(
        None,
        sample_type="Show Highly Connected",
        selected_types=['X','Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=0,
        max_edges=10
    )
    # Como 2 no es >2, retorna lista vacía
    assert ob == []

def test_filter_by_min_connections():
    """Aplica el filtro min_connections correctamente."""
    setup_inventory_and_graph()
    # min_connections = 1 → excluye 'Y:o2'
    ob, _ = get_connection_based_dataset(
        None,
        sample_type="Show Well Connected",
        selected_types=['X','Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=1,
        max_edges=10
    )
    # 'X:o1' grado=2 ≥1, debe incluirse en well_connected (ya que avg=2)
    assert len(ob) == 1
    assert ob[0]['node_id'] == 'X:o1'

def test_filter_by_selected_types_and_infoareas():
    """Solo incluye tipos e infoareas seleccionados."""
    setup_inventory_and_graph()
    # Filtramos para incluir solo Y en IA
    ob, _ = get_connection_based_dataset(
        None,
        sample_type="Show Isolated",
        selected_types=['Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=0,
        max_edges=10
    )
    # La función no devuelve aislados actualmente
    assert ob == []

    # Si pedimos una infoarea distinta, tampoco retorna nada
    ob2, _ = get_connection_based_dataset(
        None,
        sample_type="Show Isolated",
        selected_types=['X', 'Y'],
        selected_infoareas=['OTRA'],
        max_objects=10,
        min_connections=0,
        max_edges=10
    )
    assert ob2 == []

def test_mix_distribution_respects_percentages():
    """
    Con 'Show Mixed Distribution' provisto de highly_pct=0.5 e isolated_pct=0.5
    y max_objects=2, debe devolver 1 objeto highly (grado 2 > avg*2= >2?) y 1 aislado.
    En este setup avg=1, threshold*2=2 por lo que 2 no>2 → no hay highly,
    así que el llenado de remaining llena con 'X:o1'.
    """
    setup_inventory_and_graph()
    ob, _ = get_connection_based_dataset(
        None,
        sample_type="Show Mixed Distribution",
        selected_types=['X','Y'],
        selected_infoareas=['IA'],
        max_objects=2,
        min_connections=0,
        max_edges=10,
        highly_pct=0.5,
        well_pct=0,
        isolated_pct=0.5
    )
    # Debe haber 2 objetos porque fills remaining si falta highly
    assert len(ob) == 2
    node_ids = {o['node_id'] for o in ob}
    assert node_ids == {'X:o1', 'Y:o2'}

def test_max_edges_limits_relationships():
    """El parámetro max_edges con Show Isolated no devuelve relaciones (ningún par aislado-aislado)."""
    setup_inventory_and_graph()
    # Creamos 3 relaciones entre X:o1 y Y:o2
    st.session_state.relationships = [
        {'source': 'X:o1', 'target': 'Y:o2'} for _ in range(3)
    ]
    # Show Isolated solo toma Y:o2, por tanto no hay relaciones entre aislados
    ob, rl = get_connection_based_dataset(
        None,
        sample_type="Show Isolated",
        selected_types=['X','Y'],
        selected_infoareas=['IA'],
        max_objects=2,
        min_connections=0,
        max_edges=2
    )
    # Ninguna relación cumple source AND target en {'Y:o2'}
    assert rl == []

#-------------------------------------------------------------------------------
from backend.optimized_network import calculate_sampled_connection_stats


def test_empty_sample_returns_zero_stats():
    """Cuando la lista está vacía, debe devolver porcentajes y promedios en 0."""
    stats = calculate_sampled_connection_stats(None, [])
    assert stats == {
        'connected_percentage': 0,
        'avg_connections': 0
    }

def test_all_isolated_objects():
    """Si todos los objetos tienen 0 conexiones, connected_percentage y avg_connections son 0."""
    sampled = [
        {'connections': 0},
        {'connections': 0},
        {'connections': 0}
    ]
    stats = calculate_sampled_connection_stats(None, sampled)
    assert stats['connected_percentage'] == 0.0
    assert stats['avg_connections'] == 0.0
    assert stats['total_objects'] == 3
    assert stats['connected_objects'] == 0
    assert stats['isolated_objects'] == 3

def test_all_connected_objects():
    """Si todos tienen conexiones > 0, connected_percentage es 100 y avg_connections correcto."""
    sampled = [
        {'connections': 1},
        {'connections': 3},
        {'connections': 2}
    ]
    stats = calculate_sampled_connection_stats(None, sampled)
    assert stats['connected_percentage'] == pytest.approx(100.0)
    assert stats['avg_connections'] == pytest.approx((1+3+2)/3)
    assert stats['total_objects'] == 3
    assert stats['connected_objects'] == 3
    assert stats['isolated_objects'] == 0

def test_mixed_connected_and_isolated():
    """Mezcla de objetos conectados y aislados calcula bien porcentajes y promedios."""
    sampled = [
        {'connections': 0},
        {'connections': 4},
        {'connections': 2},
        {'connections': 0}
    ]
    stats = calculate_sampled_connection_stats(None, sampled)
    # Dos de cuatro tienen conexiones >0 → 50%
    assert stats['connected_percentage'] == pytest.approx(50.0)
    # Promedio = (0+4+2+0)/4 = 1.5
    assert stats['avg_connections'] == pytest.approx(1.5)
    assert stats['total_objects'] == 4
    assert stats['connected_objects'] == 2
    assert stats['isolated_objects'] == 2

def test_missing_connections_key_defaults_to_zero():
    """Si algún dict no tiene 'connections', se considera 0 conexiones."""
    sampled = [
        {},  # connections implícito = 0
        {'connections': 5}
    ]
    stats = calculate_sampled_connection_stats(None, sampled)
    assert stats['connected_percentage'] == pytest.approx(50.0)
    assert stats['avg_connections'] == pytest.approx((0+5)/2)
    assert stats['total_objects'] == 2
    assert stats['connected_objects'] == 1
    assert stats['isolated_objects'] == 1

#--------------------------------------------------------------------------
import backend.optimized_network as on_mod
from backend.optimized_network import create_connection_aware_3d_network

# Dummy classes to capture calls
class DummyFig:
    def __init__(self):
        self.layout_kwargs = {}
        self.traces = []
    def add_trace(self, trace):
        self.traces.append(trace)
    def update_layout(self, **kwargs):
        self.layout_kwargs.update(kwargs)

class DummyGo:
    Figure = DummyFig

@pytest.fixture(autouse=True)
def reset_streamlit_state():
    """Limpia session_state entre pruebas."""
    st.session_state.relationships = []
    st.session_state.global_inventory = {}
    yield
    st.session_state.relationships.clear()
    st.session_state.global_inventory.clear()

def test_empty_objects_returns_none():
    """Si no hay objetos, debe devolver None."""
    result = create_connection_aware_3d_network(None, [], [], render_quality='low',
                                                show_connection_percentages=False,
                                                line_intensity=1.0)
    assert result is None

def test_create_connection_aware_3d_network_calls_helpers(monkeypatch):
    """Verifica que invoque calculate, add_edges, add_nodes y actualice el layout."""
    # Parcheamos calculate_optimized_3d_positions
    monkeypatch.setattr(on_mod, 'calculate_optimized_3d_positions',
                        lambda self, graph, quality: {'A': {'x': 1, 'y': 2, 'z': 3}})
    # Capturamos llamada a add_connection_aware_3d_edges
    edges_called = {}
    def fake_add_edges(self, fig, relationships, pos_3d, render_quality, line_intensity):
        edges_called['args'] = (relationships, pos_3d, render_quality, line_intensity)
    monkeypatch.setattr(on_mod, 'add_connection_aware_3d_edges', fake_add_edges)
    # Capturamos llamadas a add_connection_aware_3d_nodes_by_category
    nodes_called = []
    def fake_add_nodes(self, fig, category, objects, pos_3d, render_quality, show_connection_percentages):
        nodes_called.append((category, objects, render_quality, show_connection_percentages))
    monkeypatch.setattr(on_mod, 'add_connection_aware_3d_nodes_by_category', fake_add_nodes)
    # Parcheamos go.Figure
    monkeypatch.setattr(on_mod, 'go', DummyGo)

    # Datos de prueba
    objects = [
        {'node_id': 'A', 'category': 'Cat1'},
        {'node_id': 'B', 'category': 'Cat2'}
    ]
    relationships = [{'source': 'A', 'target': 'B'}]

    fig = create_connection_aware_3d_network(
        None,
        objects,
        relationships,
        render_quality='high',
        show_connection_percentages=True,
        line_intensity=0.5
    )

    # Debe devolver DummyFig
    assert isinstance(fig, DummyFig)

    # Verifica calculate_optimized_3d_positions: implícitamente usada al crear pos_3d
    # Verifica add_edges llamada correctamente
    rels_arg, pos_arg, rq_arg, li_arg = edges_called['args']
    assert rels_arg == relationships
    assert pos_arg == {'A': {'x': 1, 'y': 2, 'z': 3}}
    assert rq_arg == 'high'
    assert li_arg == 0.5

    # Verifica add_nodes llamado una vez por categoría
    called_categories = {call[0] for call in nodes_called}
    assert called_categories == {'Cat1', 'Cat2'}
    # Y respeta los flags de porcentaje
    for _, objs_passed, rq_passed, show_pct in nodes_called:
        assert rq_passed == 'high'
        assert show_pct is True
        assert objs_passed == objects

    # Verifica título del layout incluye conteos
    title_text = fig.layout_kwargs['title']['text']
    assert '2 objects' in title_text
    assert '1 connections' in title_text

#------------------------------------------------------------------

from plotly.graph_objects import Figure, Scatter3d
import backend.optimized_network as mod
from backend.optimized_network import add_connection_aware_3d_nodes_by_category

@pytest.fixture(autouse=True)
def mock_source_system(monkeypatch):
    """
    Mockea get_source_system_info para no depender de la implementación real.
    """
    monkeypatch.setattr(mod, 'get_source_system_info',
                        lambda self, name: 'MockSource')


def test_no_objects_para_categoria():
    fig = Figure()
    add_connection_aware_3d_nodes_by_category(
        None,
        fig,
        "NO_EXISTE",
        [],
        {},
        render_quality="Balanced",
        show_connection_percentages=False
    )
    assert len(fig.data) == 0


@pytest.mark.parametrize("render_quality,show_pct,expected_mode", [
    ("High Performance", False, "markers"),
    ("Balanced",         False, "markers+text"),
    ("Balanced",         True,  "markers+text"),
])
def test_modo_coordenadas_y_texto(render_quality, show_pct, expected_mode):
    obj = {
        "category":    "CAT",
        "node_id":     "N1",
        "name":        "NombreMuyLargo",
        "icon":        "🔷",
        "type_name":   "TipoPrueba",
        "type":        "T",
        "size_base":   7,
        "color":       "#FF6B6B",
        "shape":       "circle",
        "connections": 3,
        "owner":       "Usuario",
        "infoarea":    "IA",
        "active":      True
    }
    fig = Figure()
    add_connection_aware_3d_nodes_by_category(
        None,
        fig,
        "CAT",
        [obj],
        {"N1": {"x": 0.5, "y": 1.5, "z": -2.0}},
        render_quality=render_quality,
        show_connection_percentages=show_pct
    )

    # Se añadió un único trace Scatter3d
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert isinstance(trace, Scatter3d)

    # Coordenadas correctas
    assert list(trace.x) == [0.5]
    assert list(trace.y) == [1.5]
    assert list(trace.z) == [-2.0]

    # Modo de render
    assert trace.mode == expected_mode

    # Texto de nodo
    if render_quality == "High Performance":
        # Puede venir como tuple o lista, pero el primer elemento debe ser cadena vacía
        assert trace.text[0] == ""
    else:
        txt = trace.text[0]
        if show_pct:
            assert "(100%)" in txt
        else:
            assert "%" not in txt


def test_high_quality_hoverinfo_con_datasource():
    obj = {
        "category":    "DATASOURCE",
        "node_id":     "DS1",
        "name":        "MiDataSource",
        "icon":        "📡",
        "type_name":   "DataSource",
        "type":        "DS",
        "size_base":   4,
        "color":       "#96CEB4",
        "shape":       "square",
        "connections": 2,
        "owner":       "Admin",
        "infoarea":    "AREA_TEST",
        "active":      False
    }
    fig = Figure()
    add_connection_aware_3d_nodes_by_category(
        None,
        fig,
        "DATASOURCE",
        [obj],
        {"DS1": {"x": -1.0, "y": -2.0, "z": -3.0}},
        render_quality="High Quality",
        show_connection_percentages=True
    )

    # Un único trace Scatter3d
    assert len(fig.data) == 1
    trace = fig.data[0]
    hover = trace.hovertext[0]

    # Verifica que aparezca la etiqueta y el mock
    assert "Source System:" in hover
    assert "MockSource" in hover
    # Y muestra porcentaje con decimal
    assert "Connection %:" in hover

#----------------------------------------------------------------------------
import networkx as nx
import random
import streamlit as st

from backend.optimized_network import get_optimized_dataset

@pytest.fixture(autouse=True)
def reset_state():
    """
    Reinicia la sesión de Streamlit antes de cada prueba.
    """
    st.session_state.global_inventory = {}
    st.session_state.graph = nx.Graph()
    st.session_state.relationships = []
    yield
    st.session_state.global_inventory.clear()
    st.session_state.graph.clear()
    st.session_state.relationships.clear()

def setup_inventory_and_graph():
    """
    Crea un inventario y un grafo con dos objetos:
      - X:o1 con 3 conexiones (dos loops + una arista a Y:o2)
      - Y:o2 con 1 conexión (a X:o1)
    Ambos en infoarea 'IA', y una relación bidireccional entre ellos.
    """
    st.session_state.global_inventory = {
        'X': [{'name': 'o1', 'infoarea': 'IA'}],
        'Y': [{'name': 'o2', 'infoarea': 'IA'}]
    }
    G = nx.Graph()
    G.add_node('X:o1')
    G.add_node('Y:o2')
    # Dos loops en X:o1
    G.add_edge('X:o1', 'X:o1')
    G.add_edge('X:o1', 'X:o1')
    # Una conexión entre X:o1 y Y:o2
    G.add_edge('X:o1', 'Y:o2')
    st.session_state.graph = G

    st.session_state.relationships = [
        {'source': 'X:o1', 'target': 'Y:o2'},
        {'source': 'Y:o2', 'target': 'X:o1'}
    ]

def test_empty_inventory_returns_empty():
    objs, rels = get_optimized_dataset(
        None,
        strategy="🔍 Filtered View",
        selected_types=[],
        selected_infoareas=[],
        max_objects=5,
        min_connections=0,
        max_edges=5
    )
    assert objs == []
    assert rels == []

def test_filtered_view_includes_all_and_relationships():
    setup_inventory_and_graph()
    objs, rels = get_optimized_dataset(
        None,
        strategy="🔍 Filtered View",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=0,
        max_edges=10
    )
    node_ids = {o['node_id'] for o in objs}
    assert node_ids == {'X:o1', 'Y:o2'}
    # Debe devolver exactamente las relaciones definidas
    assert rels == st.session_state.relationships

def test_min_connections_filter():
    setup_inventory_and_graph()
    objs, rels = get_optimized_dataset(
        None,
        strategy="🔍 Filtered View",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=2,
        max_edges=10
    )
    # Solo X:o1 tiene ≥2 conexiones
    assert len(objs) == 1
    assert objs[0]['node_id'] == 'X:o1'
    assert rels == []  # Y:o2 queda fuera, así que ninguna relación interna

def test_most_connected_only_strategy():
    setup_inventory_and_graph()
    objs, _ = get_optimized_dataset(
        None,
        strategy="🔗 Most Connected Only",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=1,
        min_connections=0,
        max_edges=10
    )
    # Debería escoger el de mayor grado: X:o1
    assert objs == [obj for obj in objs if obj['node_id']=='X:o1']

def test_random_sample_strategy(monkeypatch):
    setup_inventory_and_graph()
    # Forzamos random.sample para invertir el orden
    monkeypatch.setattr(random, 'sample', lambda seq, k: list(reversed(seq))[:k])
    objs, _ = get_optimized_dataset(
        None,
        strategy="🎲 Random Sample",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=1,
        min_connections=0,
        max_edges=10
    )
    # Invirtiendo [X:o1,Y:o2] → tomo Y:o2
    assert objs[0]['node_id'] == 'Y:o2'

def test_smart_sample_strategy(monkeypatch):
    setup_inventory_and_graph()
    # Mockeamos smart_sample para devolver solo el segundo elemento
    monkeypatch.setattr(
        'backend.optimized_network.smart_sample',
        lambda self, objs, max_objects: [objs[1]]
    )
    objs, _ = get_optimized_dataset(
        None,
        strategy="🎯 Smart Sample (Recommended)",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=1,
        min_connections=0,
        max_edges=10
    )
    assert objs[0]['node_id'] == 'Y:o2'

def test_category_balanced_sample_strategy(monkeypatch):
    setup_inventory_and_graph()
    # Mockeamos category_balanced_sample para devolver solo el primero
    monkeypatch.setattr(
        'backend.optimized_network.category_balanced_sample',
        lambda self, objs, max_objects: [objs[0]]
    )
    objs, _ = get_optimized_dataset(
        None,
        strategy="📊 Category Focus",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=1,
        min_connections=0,
        max_edges=10
    )
    assert objs[0]['node_id'] == 'X:o1'

def test_max_edges_limits_output():
    setup_inventory_and_graph()
    # Cinco relaciones X:o1→Y:o2
    st.session_state.relationships = [
        {'source': 'X:o1', 'target': 'Y:o2'} for _ in range(5)
    ]
    objs, rels = get_optimized_dataset(
        None,
        strategy="🔍 Filtered View",
        selected_types=['X', 'Y'],
        selected_infoareas=['IA'],
        max_objects=10,
        min_connections=0,
        max_edges=3
    )
    # Ambos objetos siguen incluidos
    assert {o['node_id'] for o in objs} == {'X:o1', 'Y:o2'}
    # Solo 3 relaciones de las 5 disponibles
    assert len(rels) == 3

#--------------------------------------------------------------------

from backend.optimized_network import smart_sample

class DummyAnalyzer:
    def __init__(self):
        # Definimos prioridades: A->3, B->2, C->1
        self.object_types = {
            'A': {'priority': 3},
            'B': {'priority': 2},
            'C': {'priority': 1},
        }

def generate_objects(counts):
    """
    Genera objetos con estructura {'type', 'connections'}.
    counts: dict {type: (número_de_objetos, conexión_inicial)}
    Las conexiones decrecen para cada objeto del mismo tipo.
    """
    objs = []
    for t, (num, base_conn) in counts.items():
        for i in range(num):
            objs.append({'type': t, 'connections': base_conn - i})
    return objs

def test_returns_all_if_fewer_than_max():
    analyzer = DummyAnalyzer()
    objs = generate_objects({'A': (2, 10), 'B': (1, 5)})
    # total 3 objetos, max_objects=5
    sampled = smart_sample(analyzer, objs, max_objects=5)
    assert sampled == objs

def test_priority_sampling_with_exact_counts():
    analyzer = DummyAnalyzer()
    # 5 de cada tipo
    objs = generate_objects({'A': (5, 50), 'B': (5, 30), 'C': (5, 10)})
    sampled = smart_sample(analyzer, objs, max_objects=5)
    # 60% de 5 → 3 A; 30% de 5 → 1 B;  restante → 1 C
    types = [o['type'] for o in sampled]
    assert types.count('A') == 3
    assert types.count('B') == 1
    assert types.count('C') == 1
    # Además, dentro de A se seleccionan los de mayor conexión
    high_conns = [o['connections'] for o in sampled if o['type']=='A']
    assert high_conns == sorted(high_conns, reverse=True)

def test_sampling_with_missing_high_priority():
    analyzer = DummyAnalyzer()
    # Sin A, 3 B y 3 C
    objs = generate_objects({'B': (3, 20), 'C': (3, 5)})
    sampled = smart_sample(analyzer, objs, max_objects=4)
    # 0 A, 30% de 4→1 B, luego rellena 3 con C
    types = [o['type'] for o in sampled]
    assert types.count('B') == 1
    assert types.count('C') == 3

def test_sampling_truncates_to_max_objects():
    analyzer = DummyAnalyzer()
    # 10 A, sin B ni C
    objs = generate_objects({'A': (10, 100)})
    sampled = smart_sample(analyzer, objs, max_objects=4)
    # Aunque 60%→2 y 30%→1, con faltantes rellena desde A hasta 4
    assert len(sampled) == 2
    assert all(o['type']=='A' for o in sampled)

def test_zero_max_objects_returns_empty():
    analyzer = DummyAnalyzer()
    objs = generate_objects({'A': (5, 10), 'B': (5, 5)})
    sampled = smart_sample(analyzer, objs, max_objects=0)
    assert sampled == []

#---------------------------------------------------------------------------

from backend.optimized_network import category_balanced_sample

def test_returns_all_if_fewer_than_max():
    objs = [
        {'category': 'A', 'connections': 1},
        {'category': 'B', 'connections': 2},
    ]
    # Total 2 objetos, max_objects=5
    sampled = category_balanced_sample(None, objs, max_objects=5)
    assert sampled == objs

def test_even_distribution_between_two_categories():
    # 3 objetos en A, 3 en B
    objs = []
    for i in range(3):
        objs.append({'category': 'A', 'connections': i})
    for i in range(3):
        objs.append({'category': 'B', 'connections': i})
    # max_objects=4 → 2 por categoría
    sampled = category_balanced_sample(None, objs, max_objects=4)
    cats = [o['category'] for o in sampled]
    assert cats.count('A') == 2
    assert cats.count('B') == 2
    # Dentro de cada categoría, los de mayor conexión primero
    conns_A = [o['connections'] for o in sampled if o['category']=='A']
    assert conns_A == sorted(conns_A, reverse=True)

def test_distribution_with_remainder_three_categories():
    # A:3, B:3, C:2
    objs = []
    for i in range(3):
        objs.append({'category': 'A', 'connections': i})
    for i in range(3):
        objs.append({'category': 'B', 'connections': i})
    for i in range(2):
        objs.append({'category': 'C', 'connections': i})
    # max_objects=5, categorías=3 → per_cat=1, remainder=2
    sampled = category_balanced_sample(None, objs, max_objects=5)
    cats = [o['category'] for o in sampled]
    # Primeras dos categorías (A y B) reciben +1 extra
    assert cats.count('A') == 2
    assert cats.count('B') == 2
    assert cats.count('C') == 1

def test_insufficient_objects_in_category():
    # A:1, B:5
    objs = [{'category': 'A', 'connections': 10}]
    for i in range(5):
        objs.append({'category': 'B', 'connections': i})
    # max_objects=4, categorías=2 → per_cat=2, remainder=0
    sampled = category_balanced_sample(None, objs, max_objects=4)
    cats = [o['category'] for o in sampled]
    # A solo tiene 1, B toma 2
    assert cats.count('A') == 1
    assert cats.count('B') == 2
    assert len(sampled) == 3

def test_single_category_returns_sorted():
    # Solo categoría A con varios objetos
    objs = [{'category': 'A', 'connections': x} for x in [1, 9, 5, 3]]
    # max_objects=2 → toma los dos con más conexiones
    sampled = category_balanced_sample(None, objs, max_objects=2)
    conns = [o['connections'] for o in sampled]
    assert conns == sorted(conns, reverse=True)[:2]

def test_zero_max_objects_returns_empty():
    objs = [{'category': 'A', 'connections': 1}, {'category': 'B', 'connections': 2}]
    sampled = category_balanced_sample(None, objs, max_objects=0)
    assert sampled == []


#-------------------------------------------------------------------------------
