"""Tests for the create_llm factory function in xeren.models."""

import os
import pytest

from xeren.models import create_llm
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.models.providers.mock import MockLLM


def test_create_llm_mock():
    llm = create_llm(provider="mock", model_id="canned-test")
    assert isinstance(llm, MockLLM)
    assert llm.config.model_id == "canned-test"


def test_create_llm_groq_defaults():
    llm = create_llm(provider="groq", api_key="test_key")
    assert isinstance(llm, LocalOpenWeightAdapter)
    assert llm.config.model_id == "llama-3.3-70b-versatile"
    assert llm._get_api_base(llm.config) == "https://api.groq.com/openai/v1"
    headers = llm._get_headers(llm.config)
    assert headers["Authorization"] == "Bearer test_key"


def test_create_llm_openai_defaults():
    llm = create_llm(provider="openai", api_key="sk-test1234567890")
    assert isinstance(llm, LocalOpenWeightAdapter)
    assert llm.config.model_id == "gpt-4o-mini"
    assert llm._get_api_base(llm.config) == "https://api.openai.com/v1"


def test_create_llm_ollama_defaults():
    llm = create_llm(provider="ollama")
    assert isinstance(llm, LocalOpenWeightAdapter)
    assert llm.config.model_id == "llama3.2"
    assert llm._get_api_base(llm.config) == "http://localhost:11434/v1"


def test_create_llm_env_fallback(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test_deepseek_token")

    llm = create_llm()
    assert isinstance(llm, LocalOpenWeightAdapter)
    assert llm.config.provider == "deepseek"
    assert llm.config.model_id == "deepseek-chat"
    assert llm._get_api_base(llm.config) == "https://api.deepseek.com/v1"
    assert llm._get_headers(llm.config)["Authorization"] == "Bearer test_deepseek_token"
