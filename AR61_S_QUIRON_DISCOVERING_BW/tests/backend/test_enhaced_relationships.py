import pytest
from backend.enhaced_relationships import analyze_enhanced_relationships
from backend.enhaced_relationships import map_sap_type_to_our_type
from connectors.sqlite_connector import get_active_objects_by_type
from backend.enhaced_relationships import build_relationship_graph
import sys
import os
import streamlit as st
import backend.enhaced_relationships as er_mod


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, query, *args, **kwargs):
        # no hacemos nada, sólo simulamos la ejecución
        pass

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, rows):
        # rows será la lista que queremos que fetchall() devuelva
        self._cursor = FakeCursor(rows)

    def cursor(self):
        return self._cursor


def test_analyze_enhanced_relationships_sin_tablas():
    """
    Si available_tables está vacío, no debe lanzarse
    excepción y debe devolver lista vacía.
    """
    result = analyze_enhanced_relationships(None, FakeConn([]), set())
    assert result == []


def test_analyze_enhanced_relationships_transformations(monkeypatch):
    """
    Con la tabla RSTRAN, debe generar relaciones de tipo 'transformation'
    según las filas devueltas por el cursor.
    """
    # 1) Datos de prueba: dos filas de RSTRAN
    fake_rows = [
        ("CUBE", "SRC1", "IOBJ", "TGT1", "TR01"),
        ("ADSO", "SRC2", "CUBE", "TGT2", "TR02"),
    ]
    conn = FakeConn(fake_rows)

    # 2) Forzamos que map_sap_type_to_our_type devuelva siempre el mismo código
    monkeypatch.setattr(
        er_mod,
        "map_sap_type_to_our_type",
        lambda self, sap_type: sap_type  # identidad
    )

    # 3) Ejecutamos sólo la parte de 'RSTRAN'
    relationships = analyze_enhanced_relationships(None, conn, {"RSTRAN"})

    # 4) Verificaciones
    assert len(relationships) == 2
    for rel, (src_tp, src_nm, tgt_tp, tgt_nm, tr_id) in zip(relationships, fake_rows):
        # Debe formatear correctamente source y target
        assert rel["source"] == f"{src_tp}:{src_nm}"
        assert rel["target"] == f"{tgt_tp}:{tgt_nm}"
        assert rel["type"] == "transformation"
        assert rel["trans_id"] == tr_id
        assert rel["source_type"] == src_tp
        assert rel["target_type"] == tgt_tp
        assert rel["source_name"] == src_nm
        assert rel["target_name"] == tgt_nm
        assert rel["weight"] == 3
        assert rel["color"].startswith("#")  # color hexadecimal


def test_analyze_enhanced_relationships_multibranch(monkeypatch):
    """
    Verifica que combina ramas de dimensiones y key figures
    cuando están presentes en available_tables.
    """
    # Filas para RSDDIMEIOBJ y RSDCUBEIOBJ
    rows_dims = [("IOBJ1", "CUBE1")]
    rows_keyf = [("IOBJ2", "CUBE2")]

    class MultiCursor:
        def __init__(self):
            self.calls = 0

        def execute(self, query, *args, **kwargs):
            self.calls += 1

        def fetchall(self):
            # La primera vez es RSTRAN (vacio), luego dims, luego keyf
            if self.calls == 1:
                return rows_dims
            elif self.calls == 2:
                return rows_keyf
            return []

    class MultiConn:
        def cursor(self):
            return MultiCursor()

    # No hace falta parchear map_sap_type_to_our_type
    # porque analyze_* usa literales 'IOBJ' y 'CUBE'

    available = {"RSDDIMEIOBJ", "RSDCUBEIOBJ"}
    rels = analyze_enhanced_relationships(None, MultiConn(), available)

    # Debe haber dos relaciones: una de tipo 'usage_dimension' y otra 'usage_keyfigure'
    types = {r["type"] for r in rels}
    assert "usage_dimension" in types
    assert "usage_keyfigure" in types

    # Verificamos detalles de cada una
    dim_rel = next(r for r in rels if r["type"] == "usage_dimension")
    assert dim_rel["source"] == "IOBJ:IOBJ1"
    assert dim_rel["target"] == "CUBE:CUBE1"
    assert dim_rel["weight"] == 2
    assert dim_rel["color"] == "#E67E22"

    keyf_rel = next(r for r in rels if r["type"] == "usage_keyfigure")
    assert keyf_rel["source"] == "IOBJ:IOBJ2"
    assert keyf_rel["target"] == "CUBE:CUBE2"
    assert keyf_rel["weight"] == 2
    assert keyf_rel["color"] == "#8E44AD"

# ------------------------------------------------------------------------
# map_sap_type_to_our_type


@pytest.mark.parametrize("sap_type, expected", [
    # Mapeos directos uno a uno
    ("CUBE", "CUBE"),
    ("MPRO", "CUBE"),
    ("ADSO", "ADSO"),
    ("ODSO", "ODSO"),
    ("DS", "DS"),
    ("IOBJ", "IOBJ"),
    # Sinónimos que apuntan a 'DS'
    ("DATASOURCE", "DS"),
    ("ISOURCE", "DS"),
    ("RSDS", "DS"),
    ("INFOSOURCE", "DS"),
    ("ROOSOURCE", "DS"),
    # Tipo desconocido → None
    ("XYZ", None),
    ("", None),
    (None, None),
])
def test_map_sap_type_to_our_type(sap_type, expected):
    """
    Verifica que map_sap_type_to_our_type devuelva el mapeo correcto
    para tipos conocidos y None para valores no definidos.
    """
    assert map_sap_type_to_our_type(None, sap_type) == expected

# -------------------------------------------------------------------------
# get_active_objects_by_type


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..", "AR61_S_QUIRON_DISCOVERING_BW")
)
sys.path.insert(0, PROJECT_ROOT)


class FakeCursorMinimal:
    def __init__(self):
        self.queries = []

    def execute(self, query, *args, **kwargs):
        self.queries.append(query)

    def fetchall(self):
        last = self.queries[-1]
        if last.strip().upper().startswith("PRAGMA TABLE_INFO"):
            # Sólo la columna KEY
            # Tupla: (cid, name, type, notnull, dflt_value, pk)
            return [(0, "KEY", None, None, None, None)]
        else:
            # Resultados de SELECT: dos filas de ejemplo
            return [("A",), ("B",)]


class FakeConnMinimal:
    def __init__(self):
        self._cursor = FakeCursorMinimal()

    def cursor(self):
        return self._cursor


class FakeCursorFull:
    def __init__(self):
        self.queries = []

    def execute(self, query, *args, **kwargs):
        self.queries.append(query)

    def fetchall(self):
        last = self.queries[-1]
        if last.strip().upper().startswith("PRAGMA TABLE_INFO"):
            # Columnas: KEY, OBJVERS, OWNER, INFOAREA, ACTIVFL, OBJSTAT, CONTTIMESTMP, CUBETYPE
            return [
                (0, "KEY", None, None, None, None),
                (1, "OBJVERS", None, None, None, None),
                (2, "OWNER", None, None, None, None),
                (3, "INFOAREA", None, None, None, None),
                (4, "ACTIVFL", None, None, None, None),
                (5, "OBJSTAT", None, None, None, None),
                (6, "CONTTIMESTMP", None, None, None, None),
                (7, "CUBETYPE", None, None, None, None),
            ]
        else:
            # Un solo resultado con todos los campos en orden
            return [
                ("A", "A", "owner1", "area1", "X", "stat1", 987654321)
            ]


class FakeConnFull:
    def __init__(self):
        self._cursor = FakeCursorFull()

    def cursor(self):
        return self._cursor


@pytest.fixture(autouse=True)
def clear_session():
    """Limpia session_state antes y después de cada test."""
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_get_active_objects_by_type_minimal():
    """
    Si solo existe la columna key_field, debe devolver objetos
    con defaults en owner, infoarea, active, status y last_changed.
    """
    config = {
        "table": "TBL",
        "key_field": "KEY",
        "name": "MyName",
        "category": "Cat",
        "color": "#FFF",
        "shape": "circle",
        "size_base": 10,
        "icon": "i",
        "z_layer": 1,
    }
    conn = FakeConnMinimal()
    objs = get_active_objects_by_type(None, conn, "TYPE", config)

    # Deben ser dos objetos: 'A' y 'B'
    names = [o["name"] for o in objs]
    assert names == ["A", "B"]

    for o in objs:
        assert o["type"] == "TYPE"
        assert o["type_name"] == "MyName"
        assert o["category"] == "Cat"
        assert o["color"] == "#FFF"
        assert o["shape"] == "circle"
        assert o["size_base"] == 10
        assert o["icon"] == "i"
        assert o["z_layer"] == 1
        # Defaults
        assert o["owner"] == "Unknown"
        assert o["infoarea"] == "UNASSIGNED"
        assert o["active"] == "Unknown"
        assert o["status"] == "Unknown"
        assert o["last_changed"] == "Unknown"


def test_get_active_objects_by_type_with_optional_columns():
    """
    Si existen columnas opcionales, deben mapearse correctamente:
    OWNER → owner, INFOAREA → infoarea, ACTIVFL 'X' → active 'Yes',
    OBJSTAT → status, CONTTIMESTMP → last_changed.
    """
    config = {
        "table": "TBL",
        "key_field": "KEY",
        "name": "MyName",
        "category": "Cat",
        "color": "#FFF",
        "shape": "circle",
        "size_base": 10,
        "icon": "i",
        "z_layer": 1,
    }
    conn = FakeConnFull()
    objs = get_active_objects_by_type(None, conn, "CUBE", config)

    # Solo un objeto en el resultado
    assert len(objs) == 1
    o = objs[0]

    assert o["name"] == "A"
    assert o["type"] == "CUBE"
    assert o["type_name"] == "MyName"
    assert o["category"] == "Cat"

    # Campos mapeados
    assert o["owner"] == "owner1"
    assert o["infoarea"] == "area1"
    assert o["active"] == "Yes"
    assert o["status"] == "stat1"
    assert o["last_changed"] == "987654321"

# --------------------------------------------------------------------------------
# build_relationship_graph


def test_build_relationship_graph_basic():
    """
    Verifica que se añadan correctamente todos los nodos y aristas
    cuando todas las relaciones apuntan a nodos existentes.
    """
    # Definimos un inventario con dos tipos y varios objetos
    global_inventory = {
        "A": [
            {"name": "1", "color": "red", "shape": "circle", "size_base": 5, "icon": "i", "z_layer": 1},
            {"name": "2", "color": "blue", "shape": "square", "size_base": 6, "icon": "j", "z_layer": 2},
        ],
        "B": [
            {"name": "X", "color": "green", "shape": "triangle", "size_base": 7, "icon": "k", "z_layer": 3},
        ],
    }
    # Relaciones que conectan únicamente nodos válidos
    relationships = [
        {"source": "A:1", "target": "B:X", "type": "t1", "weight": 1},
        {"source": "B:X", "target": "A:2", "type": "t2", "weight": 2},
        {"source": "A:2", "target": "A:1", "type": "t3", "weight": 3},
    ]

    G = build_relationship_graph(None, global_inventory, relationships)

    # Debe contener los 3 nodos
    assert set(G.nodes) == {"A:1", "A:2", "B:X"}

    # Los atributos del nodo "A:1" deben conservarse
    attrs = G.nodes["A:1"]
    assert attrs["name"] == "1"
    assert attrs["color"] == "red"
    assert attrs["shape"] == "circle"
    assert attrs["size_base"] == 5
    assert attrs["icon"] == "i"
    assert attrs["z_layer"] == 1

    # Debe contener exactamente 3 aristas
    assert G.number_of_edges() == 3
    # Y cada arista debe tener el atributo 'type' correspondiente
    assert G["A:1"]["B:X"]["type"] == "t1"
    assert G["B:X"]["A:2"]["type"] == "t2"
    assert G["A:2"]["A:1"]["type"] == "t3"


def test_build_relationship_graph_filters_missing_nodes():
    """
    Verifica que se filtren las relaciones cuyo source o target
    no existan en el grafo.
    """
    global_inventory = {
        "A": [{"name": "1"}],
    }
    relationships = [
        {"source": "A:1", "target": "A:1", "type": "self", "weight": 1},   # válido (self-loop)
        {"source": "A:1", "target": "B:2", "type": "missing_target", "weight": 2},
        {"source": "C:3", "target": "A:1", "type": "missing_source", "weight": 3},
    ]

    G = build_relationship_graph(None, global_inventory, relationships)

    # Solo debe quedar el nodo existente
    assert set(G.nodes) == {"A:1"}
    # Solo debe añadirse la self-loop
    assert list(G.edges) == [("A:1", "A:1")]
    # Y su atributo 'type' debe ser 'self'
    assert G["A:1"]["A:1"]["type"] == "self"
