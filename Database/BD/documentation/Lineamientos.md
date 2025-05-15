# Lineamientos Generales de Liquibase

#### Organización de Changelogs

Definir una estrategia de gestión de los changelogs al comienzo de un proyecto facilita la localización de un registro de cambios específico bajo demanda.

**Por Release**

Se recomienda organizar los registros de cambios por Release, ya que ofrece las siguientes ventajas:

* Facilita ver qué cambios se realizaron para cada versión.
* Los changelogs no crecen con el tiempo, ya que solo contienen cambios para una única versión.
* Los changesets se pueden reordenar según sea necesario dentro de cada changelogs.

A continuación se especifica la estructura recomendada para la organización de los changelogs por release:

```xml
proyecto/
    db/
      liquibase/
          changelog/
              db-changelog-root.xml
              releases/
                  db.changelog-01.00.xml
                  db.changelog-01.01.xml
                  db.changelog-02.00.xml
                  ...
                  ...
```

El archivo changelogs **db-changelog-root.xml** incluirá automáticamente los registros de cambios para cada versión en orden alfanumérico. **Todos los changesets en los changelogs anidado al que se hace referencia se ejecutarán en el orden en que aparecen en el archivo.**

Para esta estructura, el contenido del archivo **db-changelog-root.xml**, incluyendo los changelogs, se verá de la siguiente manera:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog xmlns="http://www.liquiba"...>
    <include file="proyecto/db/liquibase/changelog/releases/db.changelog-01.00.xml"/>
    <include file="proyecto/db/liquibase/changelog/releases/db.changelog-01.01.xml"/>
    <include file="proyecto/db/liquibase/changelog/releases/db.changelog-02.00.xml"/>
</databaseChangeLog>
```

**Por ningun motivo se deben de alterar los changesets ya insertados o manipular las tabla de control a mano, ya que esto podría provocar incosistencias que Liquibase ya no podría manejar de manera segura.
En caso de ser estrictamente necesario alterar las tablas de control, se debe notificar al equipo involucrado para detener la aplicación de cambios hasta que se realice la correción.**

* Se deberá generar un nuevo archivo changelog en cada nuevo release para poder relacionar la version de bd con la versión del código correspondiente.

### Nombrado de Changesets

Para el nombrado de los changesets se recomienda lo siguiente:

* El autor y el identificador son obligatorios ya que más de una persona podría usar el mismo valor de identificador.


```xml
<changeSet id="231206-1" author="name.lastname">  
```

- author: Se debe especificar el nombre de usuario de quien aplica los cambios.
- id: Es un número único para identificar el cambio, utilizar la fecha en que se aplica el cambio y un consecutivo
Ej: 231206-1

**Sólo se permite utilizar una combinación de id y author por cada archivo de changelogs, ya que Liquibase utiliza la combinación de autor, identificación y nombre del archivo del changelogs para crea un identificador único para cada changesets.**

[Regresar](../README.md)


