# Lenzr Server

This is a simple REST server to host and share images.

## Running the server

To run the server, you can use the following command:

```sh
uv run fastapi run src/lenzr_server/main.py
```

This will install all necessary dependencies and start the server locally.

## Tech Stack

This project is built with

* `Python` as the programming language
* `uv` as the Python package manager
* `FastAPI` as the web framework

## Contributing

This shall be a guide for contributing to the Lenzr Server project.

### Running the server in development

To automatically reload the server on code changes, you can use the following command:

```sh
uv run fastapi run --reload src/lenzr_server/main.py
```

### Project management commands

This shall include a list of commands to effectively develop on the project.

#### Add a new dependency

To add a new dependency, you can use the following command:

```sh
uv add <package_name>
```

This will also update the `uv.lock` file with the necessary changes.


#### Upgrading versions in the `uv.lock` file

To upgrade the versions of the dependencies in the `uv.lock` file, you can use the following command:

```sh
uv lock --upgrade
```
