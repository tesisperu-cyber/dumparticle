import pytest
from config.settings import Settings
from core.pipeline import run_search, EmptyEquationError


def test_config_json_se_entrega_sin_ecuacion():
    assert Settings.load("config.json").equation.strip() == ""


def test_busqueda_sin_ecuacion_falla_con_mensaje(tmp_path):
    s = Settings(equation="   ", collections=["per"], db_path=str(tmp_path / "t.db"))
    with pytest.raises(EmptyEquationError):
        run_search(s)
