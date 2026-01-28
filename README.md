# Discovery-NISAR-Static-Layers-API

## Installing and running locally

From a virtual environment running python 3.13 or later:
``` bash
pip install -e .
```

## Installing test dependencies and running tests locally

To install testing packages and run tests locally:
``` bash
pip install -e .[test]
pytest
```

## Installing and running the ruff linter/formatter

``` bash
pip install ruff
ruff format
```