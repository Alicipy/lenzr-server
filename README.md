# Lenzr Server

This is a simple REST server to host and share images.

## Tech Stack

This project is built with

* `Python` as the programming language
* `uv` as the Python package manager
* `FastAPI` as the web framework
* `SQLModel` as an ORM
* `pytest` as the testing framework
* `ruff` as a formatter
* `pre-commit` for automatic execution of checks

## Setup

### `docker-compose`

The easiest way to set up the Lenzr Server is by using `docker-compose`.

Start the server as a daemon service with

```sh
docker compose up -d
```

It is reachable on port 8000 afterwards.

To stop the server, do

```sh
docker compose down
```

### Run manually

Alternatively, you can manually run the server without Docker by executing

```sh
uv run fastapi run src/lenzr_server/main.py
```

This will install all necessary dependencies and start the server locally.

## Contributing

This shall be a guide for contributing to the Lenzr Server project.

### Installing dev dependencies

At first, install all development dependencies with

```sh
uv sync --dev
````

### Activate `pre-commit` hooks

To automatically run checks when you create a commit, install the hooks:

```sh
uv run pre-commit install
```

You can also run the checks manually with

```sh
uv run pre-commit run --all-files
```

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
