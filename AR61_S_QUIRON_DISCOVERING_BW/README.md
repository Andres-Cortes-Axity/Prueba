# Bw Discover 
By: Manuel Beltrán - Antonio Ortega

Una herramienta integral de análisis basada en Python para metadatos de SAP BW (Business Warehouse) con análisis avanzado de conexiones InfoCube, visualización de red 3D y capacidades completas de rastreo de sistemas fuente.

## 🌟 Descripción General

Este analizador SAP BW mejorado proporciona información profunda sobre su panorama SAP BW con un enfoque en dependencias de InfoCube, análisis de impacto de InfoObject y rastreo completo de linaje de datos. La herramienta cuenta con una interfaz web intuitiva construida con Streamlit y visualizaciones avanzadas de red 3D.

## 🛠️ Instalación y Requisitos

### Prerrequisitos
```bash
Python 3.8+
```

### Creación del habiente
```bash
python -m venv gevenv
```
### Activacion del hambiente
```bash
gevenv\Scripts\activate
```

### Instalación de dependencias
```bash
# Instalar dependencias
pip install -r requirements.txt
```
### Ejecución del aplicativo
```bash
# Ejecutar la aplicación
streamlit run frontend/app.py
```

## 📋 Requisitos del Sistema

### Requisitos Mínimos
- **RAM**: 8GB (16GB recomendado para grandes conjuntos de datos)
- **CPU**: Procesador multi-núcleo recomendado
- **Almacenamiento**: 2GB de espacio libre para exportaciones y procesamiento
- **Navegador**: Navegador web moderno (Chrome, Firefox, Edge, Safari)

### Guías de Rendimiento
- **Conjunto de Datos Pequeño** (<5,000 objetos): Todas las características habilitadas, sin restricciones
- **Conjunto de Datos Mediano** (5,000-10,000 objetos): Modo de rendimiento recomendado
- **Conjunto de Datos Grande** (10,000-20,000 objetos): Muestreo inteligente y vistas filtradas
- **Conjunto de Datos Muy Grande** (>20,000 objetos): Optimizaciones avanzadas requeridas

## 🗄️ Requisitos de Datos

### Formato de Base de Datos
- **Tipo**: Base de datos SQLite (.db, .sqlite, .sqlite3)
- **Contenido**: Tablas de metadatos SAP BW

### Tablas SAP BW Requeridas
- `RSDCUBE` - Definiciones de InfoCube
- `RSOADSO` - Definiciones de DSO Avanzado
- `RSDODSO` - Definiciones de DSO Clásico
- `ROOSOURCE` - Definiciones de DataSource/InfoSource
- `RSDIOBJ` - Definiciones de InfoObject
- `RSTRAN` - Definiciones de Transformación
- `RSDDIMEIOBJ` - Uso de InfoObject en dimensiones
- `RSDCUBEIOBJ` - Uso de InfoObject en InfoCubes
- `RSSELDONE` - Conexiones de DataSource
- `RSDCUBEISOURCE` - Conexiones InfoCube a InfoSource

## 📝 Licencia y Soporte

Esta herramienta se proporciona tal como está para propósitos de análisis SAP BW. Para soporte o problemas, por favor referirse a la documentación o crear reportes de problemas detallados con:
- Información del tamaño del conjunto de datos
- Mensajes de error
- Detalles del navegador y sistema
- Pasos para reproducir problemas

---

**¿Listo para analizar su panorama SAP BW? ¡Comience cargando su base de datos de metadatos y explorando las capacidades completas de análisis!** 🚀

## 📞 Información de Contacto y Soporte

### Soporte Técnico
Para obtener ayuda técnica, por favor incluya la siguiente información:
- Versión del sistema operativo
- Versión de Python
- Tamaño del conjunto de datos (número de objetos)
- Mensajes de error específicos
- Capturas de pantalla del problema

### Recursos Adicionales
- **Documentación Técnica**: Consulte los comentarios en el código fuente
- **Actualizaciones**: Verifique regularmente las nuevas versiones
- **Mejores Prácticas**: Siga las guías de rendimiento para su tamaño de datos

### Limitaciones Conocidas
- **Tamaño Máximo de Conjunto de Datos**: Recomendado <100,000 objetos
- **Memoria del Navegador**: Puede requerir aumento de límites para grandes visualizaciones
- **Compatibilidad**: Optimizado para navegadores modernos (Chrome, Firefox recomendados)

---

*Para mayor infromacion del aplicativo, puedes checar la documentacion dentro de la carpeta docs/, donde encontraras una guía completa para usar el Analizador SAP BW. Para obtener la mejor experiencia, comience con conjuntos de datos pequeños para familiarizarse con la herramienta antes de analizar entornos de producción completos.*
