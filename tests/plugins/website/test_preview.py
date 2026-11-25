"""Tests for website preview providers and safe sandboxing."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.execution import SecurityViolationError
from xeren.plugins.website.tools.preview import (
    BasePreviewProvider,
    LocalPreviewProvider,
    MockPreviewProvider,
)


def _sample_files():
    return [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html><head><title>Preview</title></head><body><h1>Hello</h1></body></html>",
            language="html",
        ),
        FileArtifact(
            file_path="styles.css",
            content="body { background: black; }",
            language="css",
        ),
    ]


def test_mock_preview_provider():
    """Verify MockPreviewProvider returns safe simulated preview with disclaimer."""
    provider = MockPreviewProvider()
    assert isinstance(provider, BasePreviewProvider)

    info = provider.prepare_preview(_sample_files(), options={"port": 3000})

    assert info.provider == "mock"
    assert "localhost:3000" in (info.preview_url or "")
    assert info.is_live is False
    assert "simulated" in info.status.lower()
    assert "no live browser" in info.message.lower()
    assert info.metadata["total_files"] == 2


def test_local_preview_provider_staging():
    """Verify LocalPreviewProvider writes files safely to sandbox workspace and outputs file:// URL."""
    provider = LocalPreviewProvider()
    info = provider.prepare_preview(_sample_files())

    assert info.provider == "local"
    assert info.preview_url is not None
    assert info.preview_url.startswith("file://")
    assert info.is_live is False
    assert "workspace_path" in info.metadata


def test_local_preview_provider_rejects_path_traversal():
    """Verify LocalPreviewProvider blocks path traversal attempts during file staging."""
    provider = LocalPreviewProvider()
    dangerous_files = [
        FileArtifact(file_path="index.html", content="<html></html>", language="html"),
        FileArtifact(file_path="../../escape.txt", content="evil payload", language="text"),
    ]

    with pytest.raises(SecurityViolationError):
        provider.prepare_preview(dangerous_files)


@pytest.mark.asyncio
async def test_preview_async():
    """Verify asynchronous preview preparation."""
    provider = MockPreviewProvider()
    info = await provider.aprepare_preview(_sample_files())

    assert info.provider == "mock"
    assert info.preview_url is not None
