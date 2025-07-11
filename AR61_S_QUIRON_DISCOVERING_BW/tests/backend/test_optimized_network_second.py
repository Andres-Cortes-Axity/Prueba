# tests/backend/test_optimized_network_create.py

import pytest
import plotly.graph_objects as real_go
from plotly.graph_objects import Figure
import networkx as nx

import backend.optimized_network as mod
from backend.optimized_network import create_optimized_3d_network

@pytest.fixture(autouse=True)
def patch_go(monkeypatch):
    """
    Asegura que mod.go apunte al módulo real de Plotly para Figure, Scatter3d, etc.
    """
    monkeypatch.setattr(mod, 'go', real_go)

def test_returns_none_when_no_objects():
    """
    Si no se pasan objetos, debe devolver None.
    """
    result = create_optimized_3d_network(None, [], [], render_quality='low')
    assert result is None

def test_full_flow_calls_helpers_and_layout(monkeypatch):
    """
    Verifica que:
      - calculate_optimized_3d_positions se llame con el DiGraph esperado y la calidad.
      - add_optimized_3d_edges se invoque solo si hay relaciones.
      - add_optimized_3d_nodes_by_category se invoque por cada categoría única.
      - El layout incluya el título con los conteos correctos.
      - Devuelva una instancia de Figure.
    """
    # Parámetros de prueba
    objects = [
        {'node_id': 'A', 'category': 'Cat1'},
        {'node_id': 'B', 'category': 'Cat2'}
    ]
    relationships = [
        {'source': 'A', 'target': 'B'}
    ]

    # Captura de calculate_optimized_3d_positions
    calls = {}
    def fake_calc(self, graph, quality):
        calls['graph_nodes'] = set(graph.nodes)
        calls['quality'] = quality
        # posiciones dummy
        return {'A': {'x': 0, 'y': 0, 'z': 0}, 'B': {'x': 1, 'y': 1, 'z': 1}}
    monkeypatch.setattr(mod, 'calculate_optimized_3d_positions', fake_calc)

    # Captura de add_optimized_3d_edges
    edges_called = []
    def fake_edges(self, fig, rels, pos, rq):
        edges_called.append((tuple(rels), rq))
    monkeypatch.setattr(mod, 'add_optimized_3d_edges', fake_edges)

    # Captura de add_optimized_3d_nodes_by_category
    nodes_called = []
    def fake_nodes(self, fig, category, objs, pos, rq):
        nodes_called.append((category, tuple(n['node_id'] for n in objs), rq))
    monkeypatch.setattr(mod, 'add_optimized_3d_nodes_by_category', fake_nodes)

    # Ejecución
    fig = create_optimized_3d_network(
        None, objects, relationships, render_quality='High'
    )

    # Resultado es Figure
    assert isinstance(fig, Figure)

    # calculate fue llamado con un DiGraph que contiene A y B, y quality 'High'
    assert calls['graph_nodes'] == {'A', 'B'}
    assert calls['quality'] == 'High'

    # Se llamó add_optimized_3d_edges exactamente una vez con nuestras relaciones
    assert len(edges_called) == 1
    rels_arg, rq_arg = edges_called[0]
    assert rels_arg == tuple(relationships)
    assert rq_arg == 'High'

    # Se llamó add_optimized_3d_nodes_by_category para Cat1 y Cat2
    called_categories = {c for c, *_ in nodes_called}
    assert called_categories == {'Cat1', 'Cat2'}
    # Y en cada llamada pasan todos los objetos y la misma quality
    for category, node_ids, rq in nodes_called:
        assert set(node_ids) == {'A', 'B'}
        assert rq == 'High'

    # El layout del Figure incluye el título con '2 objects' y '1 connections'
    title_text = fig.layout.title.text
    assert '2 objects' in title_text
    assert '1 connections' in title_text

def test_skips_edges_when_no_relationships(monkeypatch):
    """
    Cuando no hay relaciones, add_optimized_3d_edges no debe llamarse,
    pero sí add_optimized_3d_nodes_by_category por categoría.
    """
    objects = [
        {'node_id': 'X', 'category': 'C1'},
        {'node_id': 'Y', 'category': 'C2'}
    ]
    # Posiciones dummy
    monkeypatch.setattr(mod, 'calculate_optimized_3d_positions',
                        lambda self, graph, quality: {'X': {'x':0,'y':0,'z':0}, 'Y': {'x':1,'y':1,'z':1}})
    # Captura
    edges_called = []
    monkeypatch.setattr(mod, 'add_optimized_3d_edges',
                        lambda self, fig, rels, pos, rq: edges_called.append(True))
    nodes_called = []
    monkeypatch.setattr(mod, 'add_optimized_3d_nodes_by_category',
                        lambda self, fig, category, objs, pos, rq: nodes_called.append(category))

    fig = create_optimized_3d_network(None, objects, [], render_quality='low')

    # No se llamaron edges
    assert edges_called == []

    # Se llamó nodes por C1 y C2
    assert set(nodes_called) == {'C1', 'C2'}

    # Devuelve Figure incluso sin edges
    assert isinstance(fig, Figure)

#-----------------------------------------------------------------------------
import networkx as nx
import backend.optimized_network as mod
from backend.optimized_network import calculate_optimized_3d_positions

class DummyGraph(nx.Graph):
    """Extiende Graph para permitir añadir z_layer fácilmente."""
    pass

@pytest.fixture
def simple_graph():
    """
    Grafo con dos nodos:
      - 'A' con z_layer=1, sin aristas (grado=0)
      - 'B' con z_layer=2, con un loop (grado=2 tras dos self-loops)
    """
    G = DummyGraph()
    G.add_node('A', z_layer=1)
    G.add_node('B', z_layer=2)
    # Añadimos dos loops a B para grado=2
    G.add_edge('B', 'B')
    G.add_edge('B', 'B')
    return G

def test_empty_graph_returns_empty():
    """Si el grafo no tiene nodos, devuelve diccionario vacío."""
    G = nx.Graph()
    result = calculate_optimized_3d_positions(None, G, render_quality="Balanced")
    assert result == {}

def test_high_performance_uses_circular_layout(simple_graph, monkeypatch):
    """Con 'High Performance' debe usar circular_layout y escalar correctamente."""
    called = {}
    # Layout 2D fijo
    fake_pos = {'A': (1.0, 2.0), 'B': (3.0, 4.0)}
    def fake_circular(g):
        called['used'] = 'circular'
        assert set(g.nodes) == {'A', 'B'}
        return fake_pos

    monkeypatch.setattr(mod.nx, 'circular_layout', fake_circular)
    # También parcheamos spring_layout para asegurarnos de que no se llame
    monkeypatch.setattr(mod.nx, 'spring_layout', lambda *args, **kwargs: pytest.skip("No debe usar spring"))

    pos3d = calculate_optimized_3d_positions(None, simple_graph, render_quality="High Performance")

    # Verificamos que se usó circular_layout
    assert called.get('used') == 'circular'

    # Coordenadas x,y multiplicadas por 8
    assert pos3d['A']['x'] == 1.0 * 8
    assert pos3d['A']['y'] == 2.0 * 8
    assert pos3d['B']['x'] == 3.0 * 8
    assert pos3d['B']['y'] == 4.0 * 8

    # Z = base_z + z_variation
    # Para A: base_z = 1*2=2, conexiones=0 → z_variation=0 → z=2
    assert pytest.approx(pos3d['A']['z'], rel=1e-3) == 2.0
    # Para B: base_z = 2*2=4, conexiones=2 → z_variation=(2/50)*0.5=0.02 → z=4.02
    assert pytest.approx(pos3d['B']['z'], rel=1e-3) == 4.02

    # También incluye campo 'connections'
    assert pos3d['A']['connections'] == 0
    assert pos3d['B']['connections'] == 2

def test_balanced_quality_uses_medium_spring_layout(simple_graph, monkeypatch):
    """Con 'Balanced' debe usar spring_layout con k=2, iterations=20."""
    called = {}
    fake_pos = {'A': (0.1, 0.2), 'B': (0.3, 0.4)}
    def fake_spring(g, k, iterations, seed):
        called['used'] = ('spring', k, iterations, seed)
        return fake_pos

    monkeypatch.setattr(mod.nx, 'spring_layout', fake_spring)
    # Prevenir uso de circular
    monkeypatch.setattr(mod.nx, 'circular_layout', lambda g: pytest.skip("No debe usar circular"))

    pos3d = calculate_optimized_3d_positions(None, simple_graph, render_quality="Balanced")

    # Verificamos parámetros correctos
    assert called['used'] == ('spring', 2, 20, 42)
    # Chequeo básico de escala x,y
    assert pos3d['A']['x'] == pytest.approx(0.1 * 8)
    assert pos3d['B']['y'] == pytest.approx(0.4 * 8)

def test_high_quality_spring_layout_for_small_graph(simple_graph, monkeypatch):
    """Con otra calidad (p.ej. 'High Quality') y pocos nodos, usa spring_layout k=3, iterations=100."""
    called = {}
    fake_pos = {'A': (5, 6), 'B': (7, 8)}
    def fake_spring(g, k, iterations, seed):
        called['used'] = ('spring', k, iterations, seed)
        return fake_pos

    monkeypatch.setattr(mod.nx, 'spring_layout', fake_spring)
    monkeypatch.setattr(mod.nx, 'circular_layout', lambda g: pytest.skip("No debe usar circular"))

    pos3d = calculate_optimized_3d_positions(None, simple_graph, render_quality="High Quality")

    assert called['used'] == ('spring', 3, 100, 42)
    # Verificar z de A: base_z=2, conexiones=0 → z=2
    assert pytest.approx(pos3d['A']['z'], rel=1e-3) == 2.0

def test_node_count_overrides_quality_thresholds(monkeypatch):
    """
    Si el número de nodos >2000, debe usar circular_layout
    incluso con calidad 'Balanced'.
    """
    # Grafo con 2001 nodos y atributo z_layer=0
    G = nx.Graph()
    for i in range(2001):
        G.add_node(f'N{i}', z_layer=0)

    called = {}
    fake_pos = {f'N{i}': (i, -i) for i in range(2001)}

    # Definimos una función que sí devuelve fake_pos
    def fake_circular_layout(graph):
        called['used'] = 'circular'
        return fake_pos

    monkeypatch.setattr(mod.nx, 'circular_layout', fake_circular_layout)
    # Aseguramos que spring_layout no se use
    monkeypatch.setattr(mod.nx, 'spring_layout',
                        lambda *args, **kwargs: pytest.skip("No debe usar spring"))

    pos3d = calculate_optimized_3d_positions(None, G, render_quality="Balanced")

    # Verificamos que efectivamente se usó circular_layout
    assert called.get('used') == 'circular'

    # Comprobamos escala X e Y
    assert pos3d['N0']['x'] == pytest.approx(0 * 8)
    assert pos3d['N2000']['y'] == pytest.approx(-2000 * 8)

#----------------------------------------------------------------------------

import plotly.graph_objects as real_go
from plotly.graph_objects import Figure
import networkx as nx

import backend.optimized_network as mod
from backend.optimized_network import create_optimized_3d_network

@pytest.fixture(autouse=True)
def patch_go(monkeypatch):
    """
    Asegura que mod.go apunte al módulo real de Plotly,
    proporcionando Figure, Scatter3d, etc.
    """
    monkeypatch.setattr(mod, 'go', real_go)

def test_returns_none_when_no_objects():
    """Si no se pasan objetos, debe devolver None."""
    result = create_optimized_3d_network(None, [], [], render_quality='low')
    assert result is None

def test_full_flow_calls_helpers_and_layout(monkeypatch):
    """
    Verifica que:
      - calculate_optimized_3d_positions se llame con el DiGraph esperado y la calidad.
      - add_optimized_3d_edges se invoque solo si hay relaciones.
      - add_optimized_3d_nodes_by_category se invoque por cada categoría única.
      - El layout incluya el título con los conteos correctos.
      - Devuelva una instancia de Figure.
    """
    objects = [
        {'node_id': 'A', 'category': 'Cat1'},
        {'node_id': 'B', 'category': 'Cat2'}
    ]
    relationships = [{'source': 'A', 'target': 'B'}]

    # Captura calculate_optimized_3d_positions
    calls = {}
    def fake_calc(self, graph, quality):
        calls['nodes'] = set(graph.nodes)
        calls['quality'] = quality
        return {'A': {'x':0,'y':0,'z':0}, 'B': {'x':1,'y':1,'z':1}}
    monkeypatch.setattr(mod, 'calculate_optimized_3d_positions', fake_calc)

    # Captura add_optimized_3d_edges
    edges_called = []
    def fake_edges(self, fig, rels, pos, rq):
        edges_called.append((tuple(rels), rq))
    monkeypatch.setattr(mod, 'add_optimized_3d_edges', fake_edges)

    # Captura add_optimized_3d_nodes_by_category
    nodes_called = []
    def fake_nodes(self, fig, category, objs, pos, rq):
        nodes_called.append((category, tuple(o['node_id'] for o in objs), rq))
    monkeypatch.setattr(mod, 'add_optimized_3d_nodes_by_category', fake_nodes)

    fig = create_optimized_3d_network(None, objects, relationships, render_quality='High')

    # Devuelve Figure
    assert isinstance(fig, Figure)

    # calculate_optimized_3d_positions recibió el grafo correcto y la calidad
    assert calls['nodes'] == {'A', 'B'}
    assert calls['quality'] == 'High'

    # Se llamó add_optimized_3d_edges exactamente una vez
    assert len(edges_called) == 1
    rels_arg, rq_arg = edges_called[0]
    assert rels_arg == tuple(relationships)
    assert rq_arg == 'High'

    # Se llamó add_optimized_3d_nodes_by_category para Cat1 y Cat2
    cats = {c for c, _, _ in nodes_called}
    assert cats == {'Cat1', 'Cat2'}
    for _, ids, rq in nodes_called:
        assert set(ids) == {'A', 'B'}
        assert rq == 'High'

    # El layout title incluye conteos
    txt = fig.layout.title.text
    assert '2 objects' in txt
    assert '1 connections' in txt

def test_skips_edges_when_no_relationships(monkeypatch):
    """
    Si no hay relaciones, no llama a add_optimized_3d_edges
    pero sigue llamando a add_optimized_3d_nodes_by_category.
    """
    objects = [
        {'node_id': 'X', 'category': 'C1'},
        {'node_id': 'Y', 'category': 'C2'}
    ]

    # Parchar calculate_optimized_3d_positions
    monkeypatch.setattr(mod, 'calculate_optimized_3d_positions',
                        lambda self, graph, quality: {'X': {'x':0,'y':0,'z':0}, 'Y': {'x':1,'y':1,'z':1}})

    edges_called = []
    monkeypatch.setattr(mod, 'add_optimized_3d_edges',
                        lambda self, fig, rels, pos, rq: edges_called.append(True))
    nodes_called = []
    monkeypatch.setattr(mod, 'add_optimized_3d_nodes_by_category',
                        lambda self, fig, category, objs, pos, rq: nodes_called.append(category))

    fig = create_optimized_3d_network(None, objects, [], render_quality='low')

    # No se llamaron edges
    assert edges_called == []

    # Se llamó nodes por cada categoría
    assert set(nodes_called) == {'C1', 'C2'}

    # Devuelve igualmente Figure
    assert isinstance(fig, Figure)

#-----------------------------------------------------------------

import plotly.graph_objects as real_go
from plotly.graph_objects import Figure, Scatter3d

import backend.optimized_network as mod
from backend.optimized_network import add_optimized_3d_nodes_by_category

@pytest.fixture(autouse=True)
def patch_go(monkeypatch):
    """
    Asegura que mod.go apunte al módulo real de Plotly para Scatter3d.
    """
    monkeypatch.setattr(mod, 'go', real_go)

@pytest.fixture
def sample_object():
    """
    Devuelve un objeto de ejemplo con todos los atributos necesarios.
    """
    return {
        "category":    "CAT",
        "node_id":     "N1",
        "name":        "TestNombreMuyLargo",
        "icon":        "🔷",
        "type_name":   "TipoPrueba",
        "type":        "T",
        "size_base":   5,
        "color":       "#FF6B6B",
        "shape":       "circle",
        "connections": 3,
        "owner":       "Usuario",
        "infoarea":    "IA",
        "active":      True
    }

@pytest.fixture
def pos_3d():
    """
    Posiciones 3D para el nodo N1.
    """
    return {"N1": {"x": 1.0, "y": -1.0, "z": 0.5}}

def test_no_objects_returns_empty(fig=None):
    """
    Si la lista de objetos está vacía o la categoría no coincide,
    no se añade ninguna traza.
    """
    fig = Figure()
    add_optimized_3d_nodes_by_category(None, fig,
                                       category="OTRA",
                                       objects=[],
                                       pos_3d={},
                                       render_quality="Balanced")
    assert len(fig.data) == 0

@pytest.mark.parametrize("render_quality,expected_mode", [
    ("High Performance", "markers"),
    ("Balanced",         "markers+text"),
    ("High Quality",     "markers+text"),
])
def test_mode_and_coordinates_and_text(sample_object, pos_3d, render_quality, expected_mode):
    """
    Verifica:
      - modo ('markers' vs 'markers+text').
      - coordenadas x,y,z.
      - texto vacío en High Performance; con icono+nombre en otros.
    """
    fig = Figure()
    add_optimized_3d_nodes_by_category(None, fig,
                                       category="CAT",
                                       objects=[sample_object],
                                       pos_3d=pos_3d,
                                       render_quality=render_quality)
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert isinstance(trace, Scatter3d)

    # Coordenadas
    assert list(trace.x) == [1.0]
    assert list(trace.y) == [-1.0]
    assert list(trace.z) == [0.5]

    # Modo
    assert trace.mode == expected_mode

    # Texto
    txt = trace.text[0]
    if render_quality == "High Performance":
        assert txt == ""
    else:
        # Debe contener icono y parte del nombre
        assert "🔷" in txt
        assert "TestNombre" in txt

def test_hoverinfo_high_quality(sample_object, pos_3d):
    """
    Para 'High Quality', el hovertext debe incluir:
      - icono + nombre en negrita blanca.
      - Type, Category, Owner, InfoArea, Connections, Status.
    """
    fig = Figure()
    sample = sample_object.copy()
    fig = Figure()
    add_optimized_3d_nodes_by_category(None, fig,
                                       category="CAT",
                                       objects=[sample],
                                       pos_3d=pos_3d,
                                       render_quality="High Quality")
    hover = fig.data[0].hovertext[0]
    # Chequeos de fragmentos HTML
    assert "<b style='color: white;'>🔷 TestNombreMuyLargo</b>" in hover
    assert "<span style='color: #FFD700;'>Type:</span> TipoPrueba" in hover
    assert "<span style='color: #FFD700;'>Connections:</span> <b style='color: #00FF00;'>3</b>" in hover

def test_size_and_color_mapping(sample_object, pos_3d):
    """
    Verifica tamaño y color mapeado:
      - base_size=5*0.9=4.5 + bonus=min(3*2,25)=6 → total=10.5
      - color '#FF6B6B' → '#FF4444'
    """
    fig = Figure()
    add_optimized_3d_nodes_by_category(None, fig,
                                       category="CAT",
                                       objects=[sample_object],
                                       pos_3d=pos_3d,
                                       render_quality="Balanced")
    trace = fig.data[0]
    # Tamaño
    size_list = trace.marker.size
    assert pytest.approx(size_list[0], rel=1e-3) == 10.5
    # Color mapeado
    assert trace.marker.color == "#FF4444"