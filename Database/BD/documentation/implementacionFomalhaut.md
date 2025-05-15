# Implementación de Liquibase en Fomalhaut Formularios Dinámicos

A continuación, se muestra la configuración de Liquibase utilizada para la ejecución de los changelogs sobre el contenedor y desplegar la aplicación.

**Fomalhaut** es una aplicación que contiene la siguiente estructura:

* Frontend: Aplicación Angular.
* Backend: Microservicio Java.
* Base de Datos: Postgres.
    * Scripts: Archivo changelogs que contiene los cambios para la creación de las tablas consumidas por el servicio.

#### Configuración Docker Compose

Se realizaron ajustes al archivo Docker Compose para realizar la configuración de la imagen de Liquibase a utilizar, la parametrización de las carpetas y el comando a ejecutar, quedando de la siguiente manera:


```xml
version: '3'
services:
  angular-app:
    build:
      context: ./front
      dockerfile: Dockerfile
    ports:
      - 8080:80
    container_name: jsonforms-angular-app

  postgresql-db:
    build:
      context: ./bd 
      dockerfile: Dockerfile
    environment:
      POSTGRES_DB: Formularios
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 3
    container_name: jsonforms-angular-bd

  microservicio:
    build:
      context: ./backend/form-service
      dockerfile: Dockerfile
    environment:
      - DB_URL=jdbc:postgresql://postgresql-db:5432/Formularios
      - DB_USER=postgres
      - DB_PASSWORD=password
    ports:
      - "9090:9090"
    container_name: jsonforms-angular-services

  liquibase:
    image: liquibase/liquibase:4.9.1
    depends_on:
      postgresql-db:
        condition: service_healthy
    volumes:
      - ./bd/liquibase:/liquibase/app
      - ./bd/liquibase/changelog/:/liquibase/changelog/
      - ./bd/liquibase/changelog/releases/:/liquibase/changelog/releases
    command: --defaults-file=/liquibase/app/liquibase.properties update
    container_name: liquibase_container
```

Puntos a resaltar:
* Nombre de la instancia del servidor Postgres y la verificación del estado del servicio:

```xml
  postgresql-db:

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 3
    container_name: jsonforms-angular-bd
```

* Configuración del servicio de Liquibase: Nombre la imagen, la precondición del servicio disponible, las configuraciones de las rutas donde se encuentra el archivo liquibase.properties y el path del changelogs:

```xml
  liquibase:
    image: liquibase/liquibase:4.9.1
    depends_on:
      postgresql-db:
        condition: service_healthy
    volumes:
      - ./bd/liquibase:/liquibase/app
      - ./bd/liquibase/changelog/:/liquibase/changelog/
      - ./bd/liquibase/changelog/releases/:/liquibase/changelog/releases
    command: --defaults-file=/liquibase/app/liquibase.properties update
    container_name: liquibase_container
```

#### Configuración del archivo Liquibase.Properties

La configuración del archivo Liquibase.Properties se visualiza de la siguiente manera:

* Path del changelogs:

```xml
changeLogFile=./changelog/db.changelog-1.0.0.0.sql
```

* URL de conexión:

```xml
liquibase.command.url=jdbc:postgresql://postgresql-db:5432/Formularios
```

**Nota: El nombre del servidor *postgresql-db* es el mismo nombre del nombre del servicio configurado en el archivo Docker Compose.**

* Usuario de conexión:

```xml
liquibase.command.username: postgres
```

* Password de conexión:

```xml
liquibase.command.password: password
```

#### Ejecución

Para realizar el despliegue de la aplicación, es necesario abrir una terminal sobre la carpeta donde se encuentre el archivo **docker-compose.yml* y ejecutar el siguiente comando:

```bash
docker-compose up --build
```

Se iniciará el despliegue de la aplicación. En la consola se mostrarán los resultados de ejecución, puntos a resaltar:

* Creación de los contenedores:

```xml
[+] Running 5/5
 ✔ Network proy_liquibase_default        Created                                                                                0.1s
 ✔ Container jsonforms-angular-bd        Created                                                                                0.4s
 ✔ Container jsonforms-angular-app       Created                                                                                0.4s
 ✔ Container jsonforms-angular-services  Created                                                                                0.3s
 ✔ Container liquibase_container         Created                                                                                1.7s
Attaching to jsonforms-angular-app, jsonforms-angular-bd, jsonforms-angular-services, liquibase_container
```

* Contenedor de Base de Datos listo y aceptando conexiones:

```xml
jsonforms-angular-bd        | LOG:  database system is ready to accept connections
```

* Ejecución de los changesets en el contendor de Liquibase:

```xml
liquibase_container         | Running Changeset: /changelog/releases/db.changelog-1.0.0.0.yaml::231206-1::username.lastname
liquibase_container         | Running Changeset: /changelog/releases/db.changelog-1.0.0.0.yaml::231206-2::username.lastname
liquibase_container         | Running Changeset: /changelog/releases/db.changelog-1.0.0.0.yaml::231206-3::username.lastname
liquibase_container         | Liquibase command 'update' was executed successfully.
liquibase_container exited with code 0
```

[Regresar](../README.md)