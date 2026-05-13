import os


def test_tests_run_inside_astro_conda_environment() -> None:
    assert os.environ.get("CONDA_DEFAULT_ENV") == "astro"
