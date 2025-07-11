import pytest
from connectors.source_detectors import determine_infosource_type
from connectors.source_detectors import get_source_system_info


@pytest.mark.parametrize("datasource_name, expected", [
    # Empieza con '8' → Generic InfoSource
    ("8XYZ", "Generic InfoSource"),
    ("8foobar", "Generic InfoSource"),
    # Empieza con '6' → Application Component InfoSource
    ("6COMP", "Application Component InfoSource"),
    ("6abcdef", "Application Component InfoSource"),
    # Empieza con '0' y largo ≥ 9 → SAP Standard InfoSource
    ("012345678", "SAP Standard InfoSource"),
    ("0ABCDEFGH", "SAP Standard InfoSource"),
    # Contiene 'ISOURCE' (cualquier posición) → Custom InfoSource
    ("myIsOuRcE", "Custom InfoSource"),
    ("foo_ISOURCE_bar", "Custom InfoSource"),
    # Tiene '_' y la parte antes del '_' tiene longitud 3 → External DataSource
    ("ABC_DEF", "External DataSource"),
    ("xyz_123", "External DataSource"),
    # Cualquier otro caso → DataSource
    ("123", "DataSource"),
    ("datasource", "DataSource"),
    ("A_BC", "DataSource"),  # prefijo de longitud ≠ 3
])
def test_determine_infosource_type(datasource_name, expected):
    """
    Verifica que determine_infosource_type clasifique correctamente
    según las reglas de prefijo, contenido y formato.
    """
    # Pasamos None como 'self' porque la función no usa atributos de instancia
    result = determine_infosource_type(None, datasource_name)
    assert result == expected

#------------------------------------------------------------------------------------
@pytest.mark.parametrize("datasource_name, expected", [
    # 1) Prefijo de 3 caracteres antes de '_' → devuelve ese prefijo en mayúsculas
    ("ABC_123", "ABC"),
    ("abc_xyz", "ABC"),
    # 2) Prefijo que empieza con '0' y largo >= 4 antes de '_' → SAP_<cuatro primeros>
    ("0123_def", "SAP_0123"),
    ("0abc_more", "SAP_0ABC"),
    # 3) Empieza con '0' sin '_' → estándar SAP
    ("012345678", "SAP_STANDARD_0123"),   # largo >= 9
    ("0123456",   "SAP_STANDARD"),        # largo < 9
    # 4) Prefijo 'Z' o 'Y' → desarrollo custom
    ("ZXYZ",      "CUSTOM_DEVELOPMENT"),
    ("y123",      "CUSTOM_DEVELOPMENT"),
    # 5) Prefijo '8' → GENÉRICO
    ("8DATA",     "GENERIC_INFOSOURCE"),
    # 6) Prefijo '6' → componente de aplicación
    ("6ABC",      "APPLICATION_COMPONENT"),
    # 7) Contiene 'SALES' → sistema de ventas
    ("mysales_sys", "SALES_SYSTEM"),
    # 8) Contiene 'FI' o 'FINANCE' → sistema financiero
    ("finance_team", "FINANCE_SYSTEM"),
    ("myFIx",       "FINANCE_SYSTEM"),
    # 9) Contiene 'HR' o 'HUMAN' → RRHH
    ("myHumanRes",  "HR_SYSTEM"),
    ("HR_module",   "HR_SYSTEM"),
    # 10) Contiene 'MM' o 'MATERIAL' → materiales
    ("material_flow", "MATERIALS_SYSTEM"),
    ("XXmmXX",        "MATERIALS_SYSTEM"),
    # 11) Cualquier otro caso → externo
    ("UNKNOWN",    "EXTERNAL_SYSTEM"),
    ("abc",        "EXTERNAL_SYSTEM"),
])


def test_get_source_system_info_branches(datasource_name, expected):
    """
    Comprueba todas las ramas lógicas de get_source_system_info:
      1) '_' con prefijo de longitud 3
      2) '_' con prefijo '0' y longitud >=4
      3) empiece con '0' sin '_' (dos subcasos)
      4) empiece con Z/Y
      5) empiece con 8
      6) empiece con 6
      7) contenga 'SALES'
      8) contenga 'FI' o 'FINANCE'
      9) contenga 'HR' o 'HUMAN'
     10) contenga 'MM' o 'MATERIAL'
     11) caso por defecto
    """
    # Pasamos None como self porque no usa atributos de instancia
    result = get_source_system_info(None, datasource_name)
    assert result == expected