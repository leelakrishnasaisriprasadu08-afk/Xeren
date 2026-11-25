"""Tests for the 6 exact User Experience Scenarios specified in the requirements."""

from pathlib import Path

from xeren.core.runtime import XerenCore


def test_scenario_1_sales_data_auto_discovery(tmp_path: Path):
    """SCENARIO 1:

    User: "Analyze my sales data."
    Expected: Xeren discovers the relevant sales file automatically and routes to data analysis.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="sales_ws")

    (tmp_path / "sales_august.csv").write_text("item,revenue\nWidget,1200\nGadget,3400\n", encoding="utf-8")
    (tmp_path / "other_notes.txt").write_text("General notes", encoding="utf-8")

    result = core.process_goal("Analyze my sales data")

    assert result["success"] is True
    assert result["requires_workspace"] is True
    assert "sales_august.csv" in result["selected_files"]
    assert "workspace_discovery" in result["workflow"]
    assert "data" in result["workflow"]
    assert "verification" in result["workflow"]


def test_scenario_2_research_documents_auto_discovery(tmp_path: Path):
    """SCENARIO 2:

    User: "Use my research documents to explain this topic."
    Expected: Xeren discovers relevant documents automatically and routes to knowledge/RAG.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="research_ws")

    (tmp_path / "neural_networks_research.md").write_text(
        "# Neural Networks Research\nTransformers leverage multi-head self-attention mechanisms.\n",
        encoding="utf-8",
    )
    (tmp_path / "todo.txt").write_text("groceries list", encoding="utf-8")

    result = core.process_goal("Use my research documents to explain this topic")

    assert result["success"] is True
    assert result["requires_workspace"] is True
    assert any("research" in f for f in result["selected_files"])
    assert "workspace_discovery" in result["workflow"]
    assert "knowledge" in result["workflow"] or "research" in result["workflow"]
    assert "verification" in result["workflow"]


def test_scenario_3_project_coding_bug_fix(tmp_path: Path):
    """SCENARIO 3:

    User: "Find my project and fix the login bug."
    Expected: Xeren discovers the relevant project/files and routes to coding workflow.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="dev_ws")

    src_dir = tmp_path / "src" / "auth"
    src_dir.mkdir(parents=True)
    auth_file = src_dir / "login.py"
    auth_file.write_text(
        "def login(user, password):\n    if user == 'admin':\n        return True\n    return False\n",
        encoding="utf-8",
    )

    result = core.process_goal("Find my project and fix the login bug")

    assert result["success"] is True
    assert result["requires_workspace"] is True
    assert any("login.py" in f for f in result["selected_files"])
    assert "workspace_discovery" in result["workflow"]
    assert "coding" in result["workflow"]
    assert "verification" in result["workflow"]


def test_scenario_4_multi_plugin_data_website_workflow(tmp_path: Path):
    """SCENARIO 4:

    User: "Analyze the dataset and create a website explaining the results."
    Expected: Workspace -> Data -> Website -> Verification.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="dataset_ws")

    (tmp_path / "metrics_data.csv").write_text("metric,value\nconversion_rate,4.5\nbounce_rate,32.1\n", encoding="utf-8")

    result = core.process_goal("Analyze the dataset and create a website explaining the results")

    assert result["success"] is True
    assert result["requires_workspace"] is True
    assert "metrics_data.csv" in result["selected_files"]
    assert result["workflow"] == [
        "workspace_discovery",
        "data",
        "website",
        "verification",
        "experience",
        "response",
    ]


def test_scenario_5_no_relevant_file_returns_safe_notice(tmp_path: Path):
    """SCENARIO 5:

    No relevant file exists.
    Expected: Xeren asks for clarification/access without hallucinating files.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="empty_ws")

    # Only unrelated file
    (tmp_path / "grocery_list.txt").write_text("apples, milk, bread\n", encoding="utf-8")

    result = core.process_goal("Analyze quarterly sales financial performance")

    assert result["requires_workspace"] is True
    assert result["status"] == "no_files_found"
    assert result["requires_user_input"] is True
    assert result["selected_files"] == []
    assert "no relevant file" in result["response"].lower() or "clarification" in result["workflow"]


def test_scenario_6_equally_relevant_files_trigger_user_clarification(tmp_path: Path):
    """SCENARIO 6:

    Two equally relevant files exist.
    Expected: Xeren asks which one to use.
    """
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="reports_ws")

    (tmp_path / "sales_2025.csv").write_text("quarter,revenue\nQ1,100\n", encoding="utf-8")
    (tmp_path / "sales_2026.csv").write_text("quarter,revenue\nQ1,120\n", encoding="utf-8")

    result = core.process_goal("Analyze sales data")

    assert result["requires_workspace"] is True
    assert result["status"] == "ambiguous"
    assert result["ambiguity_detected"] is True
    assert result["requires_user_input"] is True
    assert "sales_2025.csv" in result["response"]
    assert "sales_2026.csv" in result["response"]
    assert "Which one" in result["response"]
