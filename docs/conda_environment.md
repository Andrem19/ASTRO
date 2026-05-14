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
conda run -n astro pytest -n 4
conda run -n astro ruff check .
conda run -n astro mypy astrology_mcp
```

All tests should be fast and parallel-safe. Run tests with pytest-xdist (`-n 4`), keep
each unit test under 1 second, and mock slow calculations, network calls,
filesystem-heavy work, and external services. Pytest prints the top 20 slowest tests at
the end of each run.

Run Alembic migrations:

```bash
conda run -n astro alembic upgrade head
conda run -n astro alembic revision --autogenerate -m "message"
```

Focused tests:

```bash
conda run -n astro pytest -n 4 tests/unit/test_natal_chart.py
conda run -n astro pytest -n 4 tests/unit/test_synastry.py
conda run -n astro pytest -n 4 tests/unit/test_transits.py
```

Do not use global Python or global pip.

`environment.yml` sets `PYTHONNOUSERSITE=1` inside `astro` so `conda run -n astro ...`
does not import packages from `~/.local`.
