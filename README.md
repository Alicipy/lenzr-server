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
* `pytest` as the testing framework

## Contributing

This shall be a guide for contributing to the Lenzr Server project.

### Installing dev dependencies

At first, install all development dependencies with

```sh
uv sync --dev
````

### Running the server in development

To automatically reload the server on code changes, you can use the following command:

```sh
uv run fastapi run --reload src/lenzr_server/main.py
```

### Running tests

To run the tests, you can use the following command:

```sh
uv run pytest
```

### Project management commands

This shall include a list of commands to effectively develop on the project.

#### Add a new dependency

To add a new dependency, you can use the following command:

```sh
uv add <package_name>
```

This will also update the `uv.lock` file with the necessary changes.

If the package is only needed for development purposes (like testing or linting), you can add it to the `dev` group:

```sh
uv add --dev <package_name>
```

#### Upgrading versions in the `uv.lock` file

To upgrade the versions of the dependencies in the `uv.lock` file, you can use the following command:

```sh
uv lock --upgrade
```
