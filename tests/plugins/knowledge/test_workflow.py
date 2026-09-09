"""Tests for KnowledgeWorkflow synchronous, asynchronous execution and error handling."""

import pytest

from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import KnowledgeInput, KnowledgeOperation
from xeren.plugins.knowledge.workflow import KnowledgeWorkflow


def test_workflow_run_query():
    """Verify synchronous workflow run handles query operation."""
    wf = KnowledgeWorkflow()
    wf.ingestion_tool.ingest_text("Xeren runtime architecture documentation.")
    inp = KnowledgeInput(query="runtime architecture")
    result = wf.run(inp)

    assert result.operation == KnowledgeOperation.QUERY
    assert result.success is True
    assert len(result.retrieved_chunks) >= 1


def test_workflow_run_ingest():
    """Verify synchronous workflow run handles ingest operation."""
    wf = KnowledgeWorkflow()
    inp = KnowledgeInput(
        operation=KnowledgeOperation.INGEST,
        texts=["Indexing new operational manual."],
    )
    result = wf.run(inp)

    assert result.operation == KnowledgeOperation.INGEST
    assert result.success is True
    assert len(result.inserted_chunk_ids) >= 1


@pytest.mark.asyncio
async def test_workflow_arun_query_and_ingest():
    """Verify asynchronous workflow run handles both query and ingest."""
    wf = KnowledgeWorkflow()
    ingest_inp = KnowledgeInput(
        operation=KnowledgeOperation.INGEST,
        texts=["Async documentation indexing."],
    )
    ingest_res = await wf.arun(ingest_inp)
    assert ingest_res.success is True
    assert len(ingest_res.inserted_chunk_ids) >= 1

    query_inp = KnowledgeInput(query="documentation indexing")
    query_res = await wf.arun(query_inp)
    assert query_res.success is True
    assert len(query_res.retrieved_chunks) >= 1


def test_plugin_execution_error_handling():
    """Verify PluginExecutionError is raised when execution encounters a fatal error."""
    plugin = KnowledgePlugin()

    # Pass completely invalid input type or dict that fails validation
    with pytest.raises(PluginExecutionError):
        plugin.execute({"operation": "query", "query": ""})

    with pytest.raises(PluginExecutionError):
        plugin.execute({"operation": "ingest"})


@pytest.mark.asyncio
async def test_plugin_async_execution_error_handling():
    """Verify PluginExecutionError is raised on async execution failure."""
    plugin = KnowledgePlugin()
    with pytest.raises(PluginExecutionError):
        await plugin.aexecute({"operation": "query", "query": ""})
