# SSSD Test Framework PoC

**Work in progress.**

## Install dependencies

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r ./requirements.txt
```

## Run tests

```
pytest --multihost-config=mhc.yaml -v
```

## Build documentation

```
source .venv/bin/activate
pip3 install -r ./docs/requirements.txt
make -C docs html
firefox docs/_build/html/index.html
```