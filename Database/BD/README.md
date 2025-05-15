# AR21_A_ANTARES_ARQUETIPO-LIQUIBASE

 **ANTARES** es un arquetipo basado en la solución de gestión de cambios de esquema de base de datos de código abierto Liquibase, que permite gestionar fácilmente las revisiones de los cambios de las bases de datos.

 **Definiciones**
 -------
 * **Changelog**: Es el archivo de registro de cambios que utiliza Liquibase basado en texto para enumerar secuencialmente todos los cambios realizados en la base de datos. Este libro de contabilidad ayuda a Liquibase a auditar la base de datos y ejecutar cualquier cambio que aún no se haya aplicado.

 * **Changeset**: Es la unidad básica de cambio en Liquibase. Almacena todos los changesets en los changelogs. Los changesets contienen tipos de cambios que especifican qué hace cada cambio, como crear una nueva tabla o agregar una columna a una tabla existente.

**Ventajas**
-------
* Administrar el control de versiones de cualquier tipo de base de datos relacional.
* Llevar una correcta administración de las bases de datos de los Clientes.
* Obtener el estado de las versiones en la que se encuentra cada uno de los ambientes.
* Realizar fácilmente la refactorización de cada uno de los modelos.
* Construir el esquema en cualquier base de datos con un sólo desarrollo.
* Integrar la administración de las bases de datos a la herramienta fácilmente.
* Flexibilidad para trabajar con casi todas las herramientas CI/CD y sus variaciones.
* Los changesets se pueden agregar fácilmente al código base sin la necesidad de cambiar a un nuevo sistema de control de código fuente.

**Lineamientos**
-------
Para más información de los lineamientos establecidos, estructura e información adicional, revise [Lineamientos Liquibase](/documentation/Lineamientos.md).

**Ejemplos y Ejercicios**
-------
 **ANTARES** contiene una serie de ejemplos y ejercicios de los principales comandos utilizados por Liquibase, para más información consulte [Ejercicios Liquibase](/documentation/ejercicios.md).

**Uso**
-------
Este arquetipo fue implementado durante el desarrollo del [*Arte AR13_A_FOMALHAUT_FORMULARIOS-DINAMICOS*](https://github.com/Axitymx/AR13_A_FOMALHAUT_FORMULARIOS-DINAMICOS), donde a través de un Docker Compose se levantan los servicios necesarios y se ejecuta el changelogs de Base de Datos por medio de un contenedor. Para más información consulte [Liquibase en FOMALHAUT](/documentation/implementacionFomalhaut.md).


## Licencia

[MIT](https://opensource.org/licenses/MIT)

![Audience](/assets/CReA.png)

