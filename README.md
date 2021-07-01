# Migrate Traefik v1 ingresses over to Traefik v2 ingressroutes with fallback

**Warning: This is still under development. Not production ready. Use with caution!**

## Usage

```bash
export KUBECONFIG=<REDACTED>
make install
make
```

## Development

### Virtual environment

```bash
poetry shell
poetry install
```

### Linter

```bash
make lint
```

### Run tests

```bash
make test
make coverage
```

### Install pre-commit hook

The Git pre-commit hook rules are defined in [.pre-commit-config.yaml](.pre-commit-config.yaml)

```bash
poetry shell
pre-commit install
```

### Git check

Check if the code can pass a git pre-commit hook.

```bash
make check
```