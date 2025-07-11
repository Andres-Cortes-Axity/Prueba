import sys
import os
import pytest
import networkx as nx
import streamlit as st

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import analyze_infocube_connections
# Aseguramos que el proyecto real esté en sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def setup_graph_and_patches(monkeypatch):
    """
    - Limpia session_state.graph antes de cada test.
    - Parches por defecto para trace_infocube_to_all_sources, 
      generate_infocube_data_lineage, get_source_system_info, determine_infosource_type.
    """
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    # Parches que devuelven valores neutrales
    monkeypatch.setattr(ia_mod, "trace_infocube_to_all_sources", lambda self, node, depth: [])
    monkeypatch.setattr(ia_mod, "generate_infocube_data_lineage", lambda self, target, visited: [])
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, name: "SYS")
    monkeypatch.setattr(ia_mod, "determine_infosource_type", lambda self, name: "IST")
    yield
    st.session_state.clear()


def test_returns_none_when_cube_not_in_graph():
    """Si el nodo CUBE:name no existe, debe devolver None."""
    result = analyze_infocube_connections(None, "C1", depth=1,
                                          include_all_sources=False,
                                          connection_types=["t"],
                                          show_lineage=False)
    assert result is None


# def test_simple_bfs_without_sources_and_lineage():
#     """
#     Con include_all_sources=False y show_lineage=False debe:
#       - Encontrar relaciones incoming y outgoing según connection_types.
#       - Rellenar connected_objects y relationships sin lineage.
#     """
#     # Preparamos grafo: DS:D1 → CUBE:C1 → IOBJ:I1, ambos con type 't'
#     g = st.session_state.graph
#     g.add_node("CUBE:C1", type="CUBE", name="C1")
#     g.add_node("DS:D1", type="DS", name="D1")
#     g.add_node("IOBJ:I1", type="IOBJ", name="I1")
#     g.add_edge("DS:D1", "CUBE:C1", type="t")
#     g.add_edge("CUBE:C1", "IOBJ:I1", type="t")

#     res = analyze_infocube_connections(None, "C1", depth=1,
#                                        include_all_sources=False,
#                                        connection_types=["t"],
#                                        show_lineage=False)
#     # Chequeos básicos
#     assert res["target_cube"] == "C1"
#     assert res["analysis_depth"] == 1
#     assert res["includes_all_sources"] is False
#     assert res["lineage_analysis"] is False

#     # Debe haber 2 relaciones encontradas
#     assert res["total_relationships"] == 2
#     directions = {r["direction"] for r in res["relationships"]}
#     assert directions == {"incoming", "outgoing"}

#     # connected_objects debe tener 'DS' e 'IOBJ'
#     assert set(res["connected_objects"].keys()) == {"DS", "IOBJ"}
#     ds_obj = res["connected_objects"]["DS"][0]
#     assert ds_obj["node_id"] == "DS:D1"
#     # Como es DS, debe incluir source_system e infosource_type
#     assert ds_obj["source_system"] == "SYS"
#     assert ds_obj["infosource_type"] == "IST"

#     io_obj = res["connected_objects"]["IOBJ"][0]
#     assert io_obj["node_id"] == "IOBJ:I1"
#     # No debe incluir source_system para IOBJ
#     assert "source_system" not in io_obj

#     # Sin lineage
#     assert res["data_lineage_paths"] == []
#     # total_objects = 2
#     assert res["total_objects"] == 2


def test_include_all_sources_traces_and_expands_neighbors(monkeypatch):
    """
    Con include_all_sources=True, debe invocar trace_infocube_to_all_sources,
    añadir esas conexiones a relationships y a visited_nodes.
    """
    # Creamos solo el nodo CUBE:C2 al inicio
    g = st.session_state.graph
    g.add_node("CUBE:C2", type="CUBE", name="C2")
    # Stub de trace_infocube_to_all_sources que devuelve un DataSource nuevo
    def fake_trace(self, node, depth):
        return [{
            "source_node": "DS:D2",
            "source_system": "SYS2",
            "connection_path": ["X"],
        }]
    monkeypatch.setattr(ia_mod, "trace_infocube_to_all_sources", fake_trace)
    # Añadimos también el nodo DS:D2 para que pos y collection funcionen
    g.add_node("DS:D2", type="DS", name="D2")

    res = analyze_infocube_connections(None, "C2", depth=2,
                                       include_all_sources=True,
                                       connection_types=[],
                                       show_lineage=False)
    # Debe incluir una relación de tipo source_connection
    src_rels = [r for r in res["relationships"] if r["type"] == "source_connection"]
    assert len(src_rels) == 1
    assert src_rels[0]["source"] == "DS:D2"
    assert src_rels[0]["target"] == "CUBE:C2"
    assert src_rels[0]["source_system"] == "SYS2"
    assert src_rels[0]["connection_path"] == ["X"]

    # connected_objects debe contener DS:D2
    assert "DS" in res["connected_objects"]
    assert any(o["node_id"] == "DS:D2" for o in res["connected_objects"]["DS"])


def test_show_lineage_invokes_generator(monkeypatch):
    """
    Con show_lineage=True, debe llamar a generate_infocube_data_lineage
    y devolver sus resultados en data_lineage_paths.
    """
    # Preparamos grafo con CUBE:C3 para pasar chequeo inicial
    g = st.session_state.graph
    g.add_node("CUBE:C3", type="CUBE", name="C3")

    # Stub de lineage
    monkeypatch.setattr(ia_mod, "generate_infocube_data_lineage", lambda self, target, visited: ["pathA", "pathB"])

    res = analyze_infocube_connections(None, "C3", depth=1,
                                       include_all_sources=False,
                                       connection_types=[],
                                       show_lineage=True)

    assert res["data_lineage_paths"] == ["pathA", "pathB"]
    assert res["lineage_analysis"] is True


#----------------------------------------------------------------------------------
import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import trace_infocube_to_all_sources

@pytest.fixture(autouse=True)
def setup_graph_and_patches(monkeypatch):
    # Reiniciamos el grafo y parcheamos los helpers de sistema/infosource
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, name: "SYS")
    monkeypatch.setattr(ia_mod, "determine_infosource_type", lambda self, name: "IST")
    yield
    st.session_state.clear()

def test_direct_datasource_connection():
    """
    Si existe un DataSource directo como predecessor de CUBE:<id>,
    debe aparecer en la lista con todos los campos correctos.
    """
    g = st.session_state.graph
    g.add_node("CUBE:CB", type="CUBE", name="CB")
    g.add_node("DS:DS1", type="DS",   name="DS1")
    # Conexión directa
    g.add_edge("DS:DS1", "CUBE:CB", type="mytype")

    result = trace_infocube_to_all_sources(None, "CUBE:CB", depth=1)
    assert len(result) == 1

    entry = result[0]
    assert entry["source_node"] == "DS:DS1"
    assert entry["target_node"] == "CUBE:CB"
    assert entry["source_name"] == "DS1"
    assert entry["source_type"] == "DataSource/InfoSource"
    assert entry["connection_type"] == "mytype"
    assert entry["depth"] == 1
    assert entry["source_system"] == "SYS"
    assert entry["infosource_type"] == "IST"
    assert entry["connection_path"] == ["DS1"]

def test_indirect_through_provider():
    """
    Si hay un proveedor intermedio (ADSO, ODSO o TRAN) entre DS y CUBE,
    se debe generar una entrada 'via_' con intermediate_node y la ruta correcta.
    """
    g = st.session_state.graph
    g.add_node("CUBE:CB2", type="CUBE", name="CB2")
    # Nodo intermedio con type_name explícito
    g.add_node("ADSO:P1", type="ADSO", name="P1", type_name="ProvType")
    g.add_node("DS:DS2", type="DS",   name="DS2")
    # DS → ADSO → CUBE
    g.add_edge("DS:DS2", "ADSO:P1", type="t1")
    g.add_edge("ADSO:P1", "CUBE:CB2", type="t2")

    result = trace_infocube_to_all_sources(None, "CUBE:CB2", depth=2)
    # Solo debería existir la conexión indirecta
    assert len(result) == 1

    entry = result[0]
    assert entry["source_node"] == "DS:DS2"
    assert entry["target_node"] == "CUBE:CB2"
    assert entry["intermediate_node"] == "ADSO:P1"
    assert entry["source_name"] == "DS2"
    assert entry["source_type"] == "DataSource/InfoSource"
    # 'via_' + type_name del proveedor
    assert entry["connection_type"] == "via_ProvType"
    assert entry["depth"] == 3  # depth+1 para esta rama
    assert entry["source_system"] == "SYS"
    assert entry["infosource_type"] == "IST"
    # path: primero DS2 luego P1
    assert entry["connection_path"] == ["DS2", "P1"]

#---------------------------------------------------------------------------------

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import generate_infocube_data_lineage

@pytest.fixture(autouse=True)
def setup_graph():
    # Limpiamos y preparamos un grafo vacío antes de cada test
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    yield
    st.session_state.clear()

def test_no_datasources_yields_empty_list():
    """
    Si visited_nodes no contiene ningún nodo DS, retorna lista vacía.
    """
    # Solo existe el InfoCube en el grafo
    st.session_state.graph.add_node("CUBE:CX", type="CUBE", name="CX")
    visited = ["CUBE:CX"]
    result = generate_infocube_data_lineage(None, "CUBE:CX", visited)
    assert result == []

def test_no_path_between_ds_and_cube_yields_empty_list():
    """
    Si hay un DS y un CUBE en visited_nodes pero no hay camino,
    retorna lista vacía.
    """
    g = st.session_state.graph
    g.add_node("DS:DS2",   type="DS",   name="DS2")
    g.add_node("CUBE:Z",   type="CUBE", name="Z")
    visited = ["DS:DS2", "CUBE:Z"]
    result = generate_infocube_data_lineage(None, "CUBE:Z", visited)
    assert result == []

def test_simple_lineage_path_with_intermediates():
    """
    Con un camino DS→ADSO→CUBE, debe generarse un único path_info
    con path_length=3 y un intermediate_objects describiendo el ADSO.
    """
    g = st.session_state.graph
    # Nodo DataSource
    g.add_node("DS:DS1",   type="DS",   name="DS1")
    # Nodo intermedio con type_name y category
    g.add_node("ADSO:P1",  type="ADSO", name="P1",
               type_name="ProvType", category="CatProv")
    # Nodo InfoCube
    g.add_node("CUBE:CB",  type="CUBE", name="CB")
    # Conexiones: DS→ADSO→CUBE
    g.add_edge("DS:DS1",   "ADSO:P1")
    g.add_edge("ADSO:P1",  "CUBE:CB")

    visited = ["DS:DS1", "ADSO:P1", "CUBE:CB"]
    result = generate_infocube_data_lineage(None, "CUBE:CB", visited)

    assert len(result) == 1
    path_info = result[0]
    # Source y target sin prefijo
    assert path_info["source"] == "DS1"
    assert path_info["target"] == "CB"
    # Longitud del camino (3 nodos)
    assert path_info["path_length"] == 3

    # Verificamos intermediate_objects
    intermediates = path_info["intermediate_objects"]
    assert len(intermediates) == 1
    step1 = intermediates[0]
    assert step1["step"] == 1
    assert step1["object_name"] == "P1"
    assert step1["object_type"] == "ProvType"
    assert step1["category"] == "CatProv"

#-----------------------------------------------------------------------------
import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import calculate_connection_percentages

@pytest.fixture(autouse=True)
def setup_globals(monkeypatch):
    # Limpiar estado antes de cada test
    st.session_state.clear()
    st.session_state.graph = nx.DiGraph()
    yield
    st.session_state.clear()


def test_empty_inventory():
    """
    Sin objetos en global_inventory, todos los conteos y porcentajes deben ser cero.
    """
    st.session_state.global_inventory = {}
    res = calculate_connection_percentages(None)

    assert res['total_objects'] == 0
    assert res['connected_objects'] == 0
    assert res['isolated_objects'] == 0
    assert res['overall_connected_percentage'] == 0.0
    assert res['isolated_percentage'] == 0.0
    assert res['max_connections'] == 0
    assert res['most_connected_object'] is None
    # Distribución de niveles debe tener todos ceros
    assert res['connection_level_distribution'] == {
        '0 (Isolated)': 0, '1-5': 0, '6-10': 0,
        '11-20': 0, '21-50': 0, '50+': 0
    }
    assert res['by_object_type'] == {}


def test_single_isolated_object():
    """
    Un único objeto sin conexiones: isolated_objects=1, isolated_percentage=100%, demás a cero.
    """
    g = st.session_state.graph
    st.session_state.global_inventory = {
        'A': [{'name': 'X', 'type_name': 'TypeA'}]
    }
    g.add_node('A:X')  # existe en el grafo, pero sin aristas

    res = calculate_connection_percentages(None)

    assert res['total_objects'] == 1
    assert res['connected_objects'] == 0
    assert res['isolated_objects'] == 1
    assert res['overall_connected_percentage'] == 0.0
    assert res['isolated_percentage'] == 100.0

    type_stats = res['by_object_type']['A']
    assert type_stats['total'] == 1
    assert type_stats['connected'] == 0
    assert type_stats['isolated'] == 1
    assert type_stats['connected_percentage'] == 0.0
    assert type_stats['average_connections'] == 0.0


def test_multiple_objects_varied_connections():
    """
    Tres objetos (2 de tipo A, 1 de tipo B) con una sola arista A:N1→B:M1:
      - total_objects=3, connected=2, isolated=1
      - distribución: 1 aislado, 2 en '1-5'
      - estadísticas por tipo correctas
      - max_connections=1, most_connected_object = A:N1
    """
    g = st.session_state.graph
    st.session_state.global_inventory = {
        'A': [
            {'name': 'N1', 'type_name': 'T1'},
            {'name': 'N2', 'type_name': 'T1'},
        ],
        'B': [
            {'name': 'M1', 'type_name': 'T2'}
        ]
    }
    # Creamos nodos y una sola arista
    g.add_node('A:N1'); g.add_node('A:N2'); g.add_node('B:M1')
    g.add_edge('A:N1', 'B:M1')

    res = calculate_connection_percentages(None)

    # Totales globales
    assert res['total_objects'] == 3
    assert res['connected_objects'] == 2
    assert res['isolated_objects'] == 1

    # Porcentajes globales (2/3 y 1/3)
    assert res['overall_connected_percentage'] == pytest.approx((2/3)*100, rel=1e-3)
    assert res['isolated_percentage'] == pytest.approx((1/3)*100, rel=1e-3)

    # Distribución de niveles
    dist = res['connection_level_distribution']
    assert dist['0 (Isolated)'] == 1
    assert dist['1-5'] == 2

    # Stats tipo A
    statsA = res['by_object_type']['A']
    assert statsA['total'] == 2
    assert statsA['connected'] == 1
    assert statsA['isolated'] == 1
    assert statsA['connected_percentage'] == pytest.approx(50.0)
    assert statsA['average_connections'] == pytest.approx(0.5)

    # Stats tipo B
    statsB = res['by_object_type']['B']
    assert statsB['total'] == 1
    assert statsB['connected'] == 1
    assert statsB['isolated'] == 0
    assert statsB['connected_percentage'] == pytest.approx(100.0)
    assert statsB['average_connections'] == pytest.approx(1.0)

    # Mayor número de conexiones y objeto más conectado
    assert res['max_connections'] == 1
    mc = res['most_connected_object']
    assert mc == {'name': 'N1', 'type': 'T1', 'connections': 1}

    # Conexiones promedio global
    assert res['average_connections'] == pytest.approx((1 + 0 + 1)/3, rel=1e-3)

#---------------------------------------------------------------------------------
import importlib
import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import prepare_infocube_connection_csv

@pytest.fixture(autouse=True)
def patch_datetime_and_helpers(monkeypatch):
    # Recargamos el módulo para limpiar parches anteriores
    importlib.reload(ia_mod)

    # Stub de datetime para fecha fija
    class FakeDateTime:
        @classmethod
        def now(cls):
            import datetime as real_dt
            return real_dt.datetime(2025, 1, 1, 12, 0, 0)
    monkeypatch.setattr(ia_mod, "datetime", FakeDateTime)

    # Stub de sistema e infosource
    monkeypatch.setattr(ia_mod, "get_source_system_info", lambda self, src: "SYSX")
    monkeypatch.setattr(ia_mod, "determine_infosource_type", lambda self, src: "ISTX")


def test_minimal_results():
    """
    Sin data_lineage_paths, ni connected_objects, ni relationships,
    solo se incluyen las secciones de encabezado, Connected Objects y Relationships.
    """
    results = {
        'target_cube': 'CB1',
        'total_objects': 0,
        'total_relationships': 0,
        'analysis_depth': 0,
        'includes_all_sources': False,
        'data_lineage_paths': [],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_infocube_connection_csv(None, results)
    lines = csv.splitlines()

    # Encabezado fijo
    assert lines[0] == "InfoCube Connection Analysis Report"
    assert lines[1] == "Target InfoCube,CB1"
    assert lines[2] == "Analysis Date,2025-01-01 12:00:00"
    assert lines[3] == "Total Connected Objects,0"
    assert lines[4] == "Total Relationships,0"
    assert lines[5] == "Analysis Depth,0"
    assert lines[6] == "Includes All Sources,False"
    # Línea en blanco
    assert lines[7] == ""

    # Connected Objects
    idx_co = lines.index("Connected Objects")
    header_co = lines[idx_co + 1]
    assert header_co.startswith("Object Name,Object Type,Category,Owner")

    # Inmediatamente después sección Relationships
    assert lines[idx_co + 2] == ""
    assert lines[idx_co + 3] == "Relationships"
    assert lines[idx_co + 4].startswith("Source Object,Target Object")


def test_with_lineage_paths():
    """
    Con data_lineage_paths no vacío, debe incluir sección Data Lineage Paths
    antes de Connected Objects, con source_system y ruta intermedia formateada.
    """
    results = {
        'target_cube': 'CB2',
        'total_objects': 0,
        'total_relationships': 0,
        'analysis_depth': 1,
        'includes_all_sources': True,
        'data_lineage_paths': [
            {
                'source': 'DS1',
                'target': 'CB2',
                'path_length': 2,
                'intermediate_objects': []
            },
            {
                'source': 'DS2',
                'target': 'CB2',
                'path_length': 3,
                'intermediate_objects': [
                    {'object_name': 'P1'},
                    {'object_name': 'P2'}
                ]
            }
        ],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_infocube_connection_csv(None, results)
    lines = csv.splitlines()

    # Sección Data Lineage Paths
    idx_dl = lines.index("Data Lineage Paths")
    assert lines[idx_dl + 1] == "Source,Source System,Target,Path Length,Intermediate Objects"
    # Primera fila sin intermediates usa 'Direct'
    assert lines[idx_dl + 2] == "DS1,SYS,CB2,2,Direct"
    # Segunda fila con intermediates 'P1 -> P2'
    assert lines[idx_dl + 3] == "DS2,SYS,CB2,3,P1 -> P2"


def test_with_connected_objects_and_relationships():
    """
    Con objetos DS y CUBE y relaciones con source_system en el rel,
    debe listarlos correctamente en Connected Objects y Relationships.
    """
    results = {
        'target_cube': 'CB3',
        'total_objects': 0,
        'total_relationships': 1,
        'analysis_depth': 2,
        'includes_all_sources': False,
        'data_lineage_paths': [],
        'connected_objects': {
            'DS': [
                {
                    'name': 'SRC',
                    'type_name': 'DataSource',
                    'category': 'Cat',
                    'owner': 'O',
                    'infoarea': 'IA',
                    'connections_in': 1,
                    'connections_out': 0,
                    'total_connections': 1,
                    'source_system': 'SYS1',
                    'infosource_type': 'IST1'
                }
            ],
            'CUBE': [
                {
                    'name': 'CBX',
                    'type_name': 'CubeType',
                    'category': 'CatC',
                    'owner': 'O2',
                    'infoarea': 'IA2',
                    'connections_in': 0,
                    'connections_out': 0,
                    'total_connections': 0
                }
            ]
        },
        'relationships': [
            {
                'source': 'DS:SRC',
                'target': 'CUBE:CBX',
                'type': 't',
                'direction': 'incoming',
                'depth': 1,
                'source_system': 'SYS1'
            }
        ]
    }

    csv = prepare_infocube_connection_csv(None, results)
    lines = csv.splitlines()

    # Connected Objects
    idx_co = lines.index("Connected Objects")
    # Fila del DS incluye SYS1 e IST1
    row_ds = lines[idx_co + 2].split(",")
    assert row_ds[:4] == ["SRC", "DataSource", "Cat", "O"]
    assert row_ds[-2] == "SYS1"
    assert row_ds[-1] == "IST1"

    # Fila del CUBE no tiene system ni infosource
    row_cube = lines[idx_co + 3].split(",")
    assert row_cube[0] == "CBX"
    assert row_cube[-2] == ""
    assert row_cube[-1] == ""

    # Relationships
    idx_rel = lines.index("Relationships")
    row_rel = lines[idx_rel + 2].split(",")
    assert row_rel == ["SRC", "CBX", "t", "incoming", "1", "SYS1"]

#---------------------------------------------------------------------------

import datetime as real_dt
import backend.infocube_analysis as ia_mod
from types import SimpleNamespace
from backend.infocube_analysis import prepare_infocube_connection_csv_with_percentages

@pytest.fixture(autouse=True)
def patch_csv_datetime(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            import datetime as real_dt
            return real_dt.datetime(2025, 1, 1, 12, 0, 0)
    monkeypatch.setattr(ia_mod, "datetime", FakeDateTime)


def test_minimal_results():
    """
    Sin data_lineage_paths, ni connected_objects, ni relationships,
    solo se incluyen las secciones de encabezado, Connected Objects y Relationships,
    con fecha fija 2025-01-01 12:00:00.
    """
    results = {
        'target_cube': 'CB1',
        'total_objects': 0,
        'total_relationships': 0,
        'analysis_depth': 0,
        'includes_all_sources': False,
        'data_lineage_paths': [],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_infocube_connection_csv(None, results)
    lines = csv.splitlines()

    # Encabezado fijo
    assert lines[0] == "InfoCube Connection Analysis Report"
    assert lines[1] == "Target InfoCube,CB1"
    assert lines[2] == "Analysis Date,2025-01-01 12:00:00"
    assert lines[3] == "Total Connected Objects,0"
    assert lines[4] == "Total Relationships,0"
    assert lines[5] == "Analysis Depth,0"
    assert lines[6] == "Includes All Sources,False"
    assert lines[7] == ""

    # Connected Objects
    idx_co = lines.index("Connected Objects")
    header_co = lines[idx_co + 1]
    assert header_co.startswith("Object Name,Object Type,Category,Owner")

    # Immediately after, Relationships
    assert lines[idx_co + 2] == ""
    assert lines[idx_co + 3] == "Relationships"
    assert lines[idx_co + 4].startswith("Source Object,Target Object")


def test_with_lineage_paths():
    """
    Con data_lineage_paths no vacío, debe incluir sección Data Lineage Paths
    antes de Connected Objects, con fecha fija y formato correcto.
    """
    # Preparamos resultados de ejemplo
    results = {
        'target_cube': 'CB2',
        'total_objects': 0,
        'total_relationships': 0,
        'analysis_depth': 1,
        'includes_all_sources': True,
        'data_lineage_paths': [
            {
                'source': 'DS1',
                'target': 'CB2',
                'path_length': 2,
                'intermediate_objects': []
            },
            {
                'source': 'DS2',
                'target': 'CB2',
                'path_length': 3,
                'intermediate_objects': [
                    {'object_name': 'P1'},
                    {'object_name': 'P2'}
                ]
            }
        ],
        'connected_objects': {},
        'relationships': []
    }

    csv = prepare_infocube_connection_csv(None, results)
    lines = csv.splitlines()

    idx_dl = lines.index("Data Lineage Paths")
    assert lines[idx_dl + 1] == "Source,Source System,Target,Path Length,Intermediate Objects"
    # Primera fila sin intermediates usa 'Direct'
    assert lines[idx_dl + 2] == "DS1,SYS,CB2,2,Direct"
    # Segunda fila con intermediates
    assert lines[idx_dl + 3] == "DS2,SYS,CB2,3,P1 -> P2"

#--------------------------------------------------------------------------------

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import (
    create_infocube_connection_3d_visualization,
    calculate_infocube_analysis_positions
)

def test_create_3d_visualization_returns_none_on_empty():
    """Si no hay objetos, debe devolver None."""
    assert create_infocube_connection_3d_visualization(None, [], [], "C1") is None

def test_create_3d_visualization_calls_helpers(monkeypatch):
    """
    Con objetos y relaciones válidas, debe:
      - Instanciar FakeGo.Figure()
      - Llamar a calculate_infocube_analysis_positions con grafo enfocado y CUBE:<target>
      - Invocar add_infocube_analysis_edges y add_infocube_analysis_nodes
      - Configurar el título correctamente
    """
    # Preparamos datos de entrada
    objects = [
        {'node_id': 'CUBE:C1', 'name': 'C1', 'type': 'CUBE'},
        {'node_id': 'DS:D1',   'name': 'D1', 'type': 'DS'},
    ]
    relationships = [
        {'source': 'DS:D1', 'target': 'CUBE:C1', 'type': 't'}
    ]
    target = "C1"

    # Stub de go.Figure -> FakeFig
    class FakeFig:
        def __init__(self):
            self.layout_kwargs = {}
        def update_layout(self, **kwargs):
            self.layout_kwargs.update(kwargs)
    monkeypatch.setattr(ia_mod.go, "Figure", FakeFig)

    # Stub de calculate_infocube_analysis_positions
    fake_pos = {'CUBE:C1': {'x': 0, 'y': 0, 'z': 0}, 'DS:D1': {'x': 1, 'y': 2, 'z': 3}}
    called = {}
    def fake_calc(self, graph, node):
        called['graph'] = graph
        called['node'] = node
        return fake_pos
    monkeypatch.setattr(ia_mod, "calculate_infocube_analysis_positions", fake_calc)

    # Stubs de edge/node helpers
    edge_called = {}
    def fake_add_edges(self, fig, rels, pos):
        edge_called['fig'] = fig
        edge_called['rels'] = rels
        edge_called['pos'] = pos
    node_called = {}
    def fake_add_nodes(self, fig, objs, pos, tgt):
        node_called['fig'] = fig
        node_called['objs'] = objs
        node_called['pos'] = pos
        node_called['tgt'] = tgt
    monkeypatch.setattr(ia_mod, "add_infocube_analysis_edges", fake_add_edges)
    monkeypatch.setattr(ia_mod, "add_infocube_analysis_nodes", fake_add_nodes)

    fig = create_infocube_connection_3d_visualization(None, objects, relationships, target)

    # Verificaciones
    assert isinstance(fig, FakeFig)
    # calculate_infocube_analysis_positions
    assert called['node'] == f"CUBE:{target}"
    # add_edges recibió el mismo fig, relationships y posiciones
    assert edge_called['fig'] is fig
    assert edge_called['rels'] is relationships
    assert edge_called['pos'] is fake_pos
    # add_nodes recibió fig, objects, posiciones y target
    assert node_called['fig'] is fig
    assert node_called['objs'] is objects
    assert node_called['pos'] is fake_pos
    assert node_called['tgt'] == target
    # Título del layout
    title = fig.layout_kwargs['title']
    assert title['text'] == f"🧊 InfoCube Connection Analysis: {target}"
    assert title['x'] == 0.5

def test_compute_positions_categories(monkeypatch):
    """
    Debe asignar posiciones desde calculate_infocube_analysis_positions según:
      - target al centro
      - DS en source_nodes
      - predecesores en feeding_nodes
      - sucesores en consuming_nodes
      - resto en other_nodes
    y llamar a position_nodes_in_circle 4 veces.
    """
    g = nx.DiGraph()
    # Nodo target
    g.add_node("CUBE:CX", type="CUBE")
    # DataSource
    g.add_node("DS:D1", type="DS")
    # Feeding: ADSO->CUBE
    g.add_node("ADSO:P1", type="ADSO")
    g.add_edge("ADSO:P1", "CUBE:CX")
    # Consuming: CUBE->TRAN
    g.add_node("TRAN:T1", type="TRAN")
    g.add_edge("CUBE:CX", "TRAN:T1")
    # Other: IOBJ
    g.add_node("IOBJ:I1", type="IOBJ")

    calls = []
    def fake_pos(self, nodes, pos_dict, **kwargs):
        # registra la llamada y simula asignar coords
        calls.append((tuple(nodes), kwargs))
        for i, n in enumerate(nodes):
            pos_dict[n] = {'x': i, 'y': i+1, 'z': i+2}

    monkeypatch.setattr(ia_mod, "position_nodes_in_circle", fake_pos)

    pos = calculate_infocube_analysis_positions(None, g, "CUBE:CX")

    # Siempre incluye el centro
    assert pos["CUBE:CX"] == {'x': 0, 'y': 0, 'z': 0}
    # Las cuatro categorías: source_nodes, feeding, consuming, other
    assert len(calls) == 4
    # Cada llamada debe cubrir los nodos correctos
    cat_nodes = [set(c[0]) for c in calls]
    assert set(cat_nodes[0]) == {"DS:D1"}
    assert set(cat_nodes[1]) == {"ADSO:P1"}
    assert set(cat_nodes[2]) == {"TRAN:T1"}
    assert set(cat_nodes[3]) == {"IOBJ:I1"}
    # Y el diccionario pos contiene todas las entradas
    for node in ["CUBE:CX","DS:D1","ADSO:P1","TRAN:T1","IOBJ:I1"]:
        assert node in pos

#-----------------------------------------------------------------------------------

import math
import random
import pytest

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import position_nodes_in_circle

@pytest.fixture(autouse=True)
def patch_random(monkeypatch):
    # Para que las variaciones aleatorias sean siempre cero y deterministas
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)

def test_empty_nodes_does_nothing():
    """Si la lista de nodos está vacía, pos_3d no sufre cambios."""
    pos = {}
    position_nodes_in_circle(None, [], pos)
    assert pos == {}

@pytest.mark.parametrize("x_off,y_off,z_off,center_z,radius", [
    (10, 20, 5, 5, 1),
    (0, 0, 0, 2, 3),
])
def test_single_node_positions_at_offsets(x_off, y_off, z_off, center_z, radius):
    """
    Con un único nodo, debe quedar exactamente en (x_offset, y_offset, center_z+z_offset).
    """
    pos = {}
    position_nodes_in_circle(None, ["N1"], pos,
                             center_z=center_z,
                             radius=radius,
                             x_offset=x_off,
                             y_offset=y_off,
                             z_offset=z_off)
    assert "N1" in pos
    assert pos["N1"] == {"x": x_off, "y": y_off, "z": center_z + z_off}

def test_two_nodes_evenly_spaced():
    """
    Con dos nodos y sin offsets, los ángulos son 0 y π, por lo que las coordenadas
    deben ser (radius, 0, center_z) y (-radius, 0, center_z).
    """
    pos = {}
    position_nodes_in_circle(None, ["A", "B"], pos,
                             center_z=0,
                             radius=2,
                             x_offset=0,
                             y_offset=0,
                             z_offset=0)
    # A: ángulo 0 → (2,0,0), B: ángulo π → (-2,0,0)
    assert pos["A"] == pytest.approx({"x": 2.0, "y": 0.0, "z": 0.0})
    assert pos["B"] == pytest.approx({"x": -2.0, "y": 0.0, "z": 0.0})

def test_multiple_nodes_circle_layout():
    """
    Con varios nodos sin offsets, comprueba que cada uno caiga en su posición teórica
    sin variación aleatoria.
    """
    nodes = ["N0", "N1", "N2", "N3"]
    n = len(nodes)
    pos = {}
    position_nodes_in_circle(None, nodes, pos,
                             center_z=1,
                             radius=5,
                             x_offset=1,
                             y_offset=-1,
                             z_offset=2)
    # Calculamos posiciones esperadas manualmente
    step = 2 * math.pi / n
    expected = {}
    for i, node in enumerate(nodes):
        angle = i * step
        x = 5 * math.cos(angle) + 1
        y = 5 * math.sin(angle) - 1
        z = 1 + 2
        expected[node] = {"x": x, "y": y, "z": z}

    for node in nodes:
        assert pos[node] == pytest.approx(expected[node])

#-----------------------------------------------------------------------------

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import add_infocube_analysis_edges

# Fakes para capturar trazas
class FakeFig:
    def __init__(self):
        self.traces = []
    def add_trace(self, trace):
        self.traces.append(trace)

class FakeScatter3d:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

@pytest.fixture(autouse=True)
def patch_scatter(monkeypatch):
    # Sustituir go.Scatter3d por nuestro fake
    monkeypatch.setattr(ia_mod.go, "Scatter3d", FakeScatter3d)


def test_no_edges_y_no_trazas():
    """Si no hay relaciones, no se debe llamar a add_trace."""
    fig = FakeFig()
    add_infocube_analysis_edges(None, fig, [], {})
    assert fig.traces == []


def test_solo_feeding_edges(monkeypatch):
    """
    Con una sola relación incoming (no source_connection),
    debe agregarse una traza 'Data Feeding InfoCube'.
    """
    # Relación entrante
    relationships = [
        {'source': 'A', 'target': 'B', 'direction': 'incoming'}
    ]
    pos = {
        'A': {'x': 0, 'y': 0, 'z': 0},
        'B': {'x': 2, 'y': 2, 'z': 2}
    }
    fig = FakeFig()
    add_infocube_analysis_edges(None, fig, relationships, pos)

    # Solo una traza
    assert len(fig.traces) == 1
    trace = fig.traces[0]
    # Modo y nombre
    assert trace.kwargs['mode'] == 'lines'
    assert trace.kwargs['name'].startswith("⬅️ Data Feeding InfoCube")
    # Coordenadas: [x0, x1, None], etc.
    assert trace.kwargs['x'] == [0, 2, None]
    assert trace.kwargs['y'] == [0, 2, None]
    assert trace.kwargs['z'] == [0, 2, None]


def test_solo_consuming_edges():
    """
    Con una sola relación outgoing (no source_connection),
    debe agregarse una traza 'InfoCube Data Usage'.
    """
    relationships = [
        {'source': 'X', 'target': 'Y', 'direction': 'outgoing'}
    ]
    pos = {
        'X': {'x': 1, 'y': 1, 'z': 1},
        'Y': {'x': 3, 'y': 3, 'z': 3}
    }
    fig = FakeFig()
    add_infocube_analysis_edges(None, fig, relationships, pos)

    assert len(fig.traces) == 1
    trace = fig.traces[0]
    assert trace.kwargs['name'].startswith("➡️ InfoCube Data Usage")
    assert trace.kwargs['x'] == [1, 3, None]
    assert trace.kwargs['y'] == [1, 3, None]
    assert trace.kwargs['z'] == [1, 3, None]


def test_solo_source_edges():
    """
    Con una relación tipo 'source_connection',
    debe agregarse una traza 'Source Connections'.
    """
    relationships = [
        {'source': 'S', 'target': 'T', 'type': 'source_connection', 'direction': 'incoming'}
    ]
    pos = {
        'S': {'x': -1, 'y': -1, 'z': -1},
        'T': {'x': -2, 'y': -2, 'z': -2}
    }
    fig = FakeFig()
    add_infocube_analysis_edges(None, fig, relationships, pos)

    assert len(fig.traces) == 1
    trace = fig.traces[0]
    assert trace.kwargs['name'].startswith("📡 Source Connections")
    assert trace.kwargs['line']['width'] == 6  # estilo diferente
    assert trace.kwargs['x'] == [-1, -2, None]
    assert trace.kwargs['y'] == [-1, -2, None]
    assert trace.kwargs['z'] == [-1, -2, None]


def test_mezcla_de_tres_tipos():
    """
    Con relaciones feeding, consuming y source_connection,
    produce tres trazas en el orden: feeding, consuming, source.
    """
    relationships = [
        {'source': 'A', 'target': 'B', 'direction': 'incoming'},
        {'source': 'B', 'target': 'C', 'direction': 'outgoing'},
        {'source': 'X', 'target': 'Y', 'type': 'source_connection', 'direction': 'incoming'}
    ]
    pos = {
        'A': {'x': 0, 'y': 0, 'z': 0},
        'B': {'x': 1, 'y': 1, 'z': 1},
        'C': {'x': 2, 'y': 2, 'z': 2},
        'X': {'x': 3, 'y': 3, 'z': 3},
        'Y': {'x': 4, 'y': 4, 'z': 4},
    }
    fig = FakeFig()
    add_infocube_analysis_edges(None, fig, relationships, pos)

    assert len(fig.traces) == 3
    names = [t.kwargs['name'] for t in fig.traces]
    assert any(n.startswith("⬅️ Data Feeding InfoCube") for n in names)
    assert any(n.startswith("➡️ InfoCube Data Usage") for n in names)
    assert any(n.startswith("📡 Source Connections") for n in names)

#----------------------------------------------------------------------------

import backend.infocube_analysis as ia_mod
from backend.infocube_analysis import add_infocube_analysis_nodes

# Fakes para capturar trazas
class FakeFig:
    def __init__(self):
        self.traces = []
    def add_trace(self, trace):
        self.traces.append(trace)

class FakeScatter3d:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

@pytest.fixture(autouse=True)
def patch_scatter(monkeypatch):
    # Stub de go.Scatter3d para pruebas
    monkeypatch.setattr(ia_mod.go, "Scatter3d", FakeScatter3d)

def test_no_objects_no_traces():
    """Si no hay objetos, no se deben añadir trazas."""
    fig = FakeFig()
    add_infocube_analysis_nodes(None, fig, [], {}, "C1")
    assert fig.traces == []

def test_add_target_highlight_trace(monkeypatch):
    """Con solo el objeto target, se añade una única traza marcada como target."""
    # Posición del nodo
    pos = {"CUBE:C1": {"x": 0, "y": 0, "z": 0}}
    # Objeto target
    objs = [{"node_id": "CUBE:C1", "name": "C1", "type": "CUBE", "type_name": "InfoCube", "is_target": True}]
    fig = FakeFig()
    add_infocube_analysis_nodes(None, fig, objs, pos, "C1")

    assert len(fig.traces) == 1
    t = fig.traces[0]
    # Verificamos que el nombre de la traza contenga el target
    assert t.kwargs["name"] == "🧊 Target: C1"
    # Modo markers+text
    assert t.kwargs["mode"] == "markers+text"
    # Coordenadas del marker
    assert t.kwargs["x"] == [0]
    assert t.kwargs["y"] == [0]
    assert t.kwargs["z"] == [0]
    # Hovertemplate contiene el nombre
    assert "TARGET INFOCUBE" in t.kwargs["hovertemplate"]
    assert "C1" in t.kwargs["hovertemplate"]

def test_add_source_objects_trace():
    """Con objetos de tipo DS, se añade una traza para DataSources."""
    pos = {
        "DS:D1": {"x": 1, "y": 2, "z": 3}
    }
    objs = [
        {"node_id": "DS:D1", "name": "D1", "type": "DS", "size_base": 10,
         "total_connections": 2, "source_system": "SYS", "infosource_type": "IST", "icon": "📡", 
         "owner": "O", "infoarea": "IA"}
    ]
    fig = FakeFig()
    add_infocube_analysis_nodes(None, fig, objs, pos, "C1")

    # Debe generar exactamente 1 traza para fuentes
    assert len(fig.traces) == 1
    t = fig.traces[0]
    assert t.kwargs["name"].startswith("📡 DataSources/InfoSources")
    # Modo markers+text y símbolo
    assert t.kwargs["mode"] == "markers+text"
    # Debe usar icono en text
    assert any("📡" in txt for txt in t.kwargs["text"])
    # Hovertext contiene Source System e InfoSource Type
    assert "Source System: SYS" in t.kwargs["hovertext"][0]
    assert "Type: IST" in t.kwargs["hovertext"][0]

def test_add_other_objects_by_category():
    """Objetos no target ni DS se agrupan por categoría y se añade una traza por categoría."""
    pos = {
        "IOBJ:I1": {"x": 0, "y": 0, "z": 0},
        "IOBJ:I2": {"x": 1, "y": 1, "z": 1},
        "CUBE:C2": {"x": 2, "y": 2, "z": 2}
    }
    objs = [
        {
            "node_id": "CUBE:C2",
            "name": "C2",
            "type": "CUBE",
            "type_name": "InfoCube",
            "icon": "🧊",
            "category": "CatA",
            "color": "#FF6B6B",      # agregado
            "size_base": 10,
            "total_connections": 1,
            "owner": "O1",
            "infoarea": "IA1"
        },
        {
            "node_id": "IOBJ:I1",
            "name": "I1",
            "type": "IOBJ",
            "type_name": "InfoObject",
            "icon": "🏷️",
            "category": "CatB",
            "color": "#FFEAA7",      # agregado
            "size_base": 12,
            "total_connections": 0,
            "owner": "O2",
            "infoarea": "IA2"
        },
        {
            "node_id": "IOBJ:I2",
            "name": "I2",
            "type": "IOBJ",
            "type_name": "InfoObject",
            "icon": "🏷️",
            "category": "CatB",
            "color": "#FFEAA7",      # agregado
            "size_base": 12,
            "total_connections": 2,
            "owner": "O3",
            "infoarea": "IA3"
        }
    ]
    fig = FakeFig()
    add_infocube_analysis_nodes(None, fig, objs, pos, "C1")

    # Deben ser dos trazas: una para CatA (CUBE) y otra para CatB (IOBJ)
    assert len(fig.traces) == 2
    names = {t.kwargs["name"] for t in fig.traces}
    assert any("CatA" in name for name in names)
    assert any("CatB" in name for name in names)