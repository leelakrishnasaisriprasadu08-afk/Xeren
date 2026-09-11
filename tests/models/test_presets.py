"""Unit tests for standalone LLM model presets."""

import pytest

from xeren.models.presets import (
    MODEL_PRESETS,
    get_model_preset,
    get_presets_by_temperature_range,
    list_model_presets,
)


def test_preset_count_is_twenty() -> None:
    presets = list_model_presets()
    assert len(presets) == 20
    assert len(MODEL_PRESETS) == 20


def test_preset_temperatures_span_zero_to_one() -> None:
    presets = list_model_presets()
    temperatures = [round(m.temperature, 2) for m in presets]

    expected = [
        0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00,
    ]
    assert temperatures == expected


def test_midpoint_is_multiturn_refactor_not_natural_dialogue() -> None:
    p50 = get_model_preset("xeren-tempo-50-multiturn-refactor")
    assert p50 is not None
    assert p50.temperature == 0.50
    assert "multiturn_refactor" in p50.extra_params.get("tempo_tier", "")
    assert "dialogue" not in p50.extra_params.get("description", "").lower()
    # Confirm default natural dialogue is not in presets (reserved for Xeren-Mini)
    assert "xeren-tempo-50-natural-dialogue" not in MODEL_PRESETS


def test_presets_are_disconnected_for_future_development() -> None:
    for model_id, config in MODEL_PRESETS.items():
        assert config.extra_params.get("active") is False, f"Model {model_id} must be inactive"
        assert config.provider == "local_openweight"
        assert config.timeout_seconds > 0


def test_get_model_preset() -> None:
    m00 = get_model_preset("xeren-tempo-00-deterministic")
    assert m00 is not None
    assert m00.temperature == 0.00
    assert m00.top_p == 0.10

    m100 = get_model_preset("xeren-tempo-100-creative-wildcard")
    assert m100 is not None
    assert m100.temperature == 1.00

    assert get_model_preset("non_existent_preset") is None


def test_get_presets_by_temperature_range() -> None:
    code_models = get_presets_by_temperature_range(0.10, 0.25)
    assert len(code_models) == 4
    for m in code_models:
        assert 0.10 <= m.temperature <= 0.25

    creative_models = get_presets_by_temperature_range(0.80, 1.00)
    assert len(creative_models) == 4
    for m in creative_models:
        assert 0.80 <= m.temperature <= 1.00
