# Conda Environment

All Python, Alembic, test, lint, and type-check commands must run inside conda environment
`astro`.

Create the environment:

```bash
conda env create -f environment.yml
conda activate astro
python -m pip install -e .
```

Update an existing environment:

```bash
conda env update -n astro -f environment.yml --prune
conda activate astro
python -m pip install -e .
```

Without shell activation:

```bash
conda run -n astro python -m pip install -e .
conda run -n astro alembic upgrade head
conda run -n astro python -m astrology_mcp.main
```

Run the server:

```bash
conda activate astro
alembic upgrade head
python -m astrology_mcp.main
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Run checks:

```bash
conda run -n astro pytest
conda run -n astro ruff check .
conda run -n astro mypy astrology_mcp
```

Run Alembic migrations:

```bash
conda run -n astro alembic upgrade head
conda run -n astro alembic revision --autogenerate -m "message"
```

Focused tests:

```bash
conda run -n astro pytest tests/unit/test_natal_chart.py
conda run -n astro pytest tests/unit/test_synastry.py
conda run -n astro pytest tests/unit/test_transits.py
```

Do not use global Python or global pip.

`environment.yml` sets `PYTHONNOUSERSITE=1` inside `astro` so `conda run -n astro ...`
does not import packages from `~/.local`.
