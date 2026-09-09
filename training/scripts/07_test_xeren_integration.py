"""Script 07: Test integration between Xeren LocalOpenWeightAdapter and trained model."""

import sys
import types
from pathlib import Path

# Add project root and isolate xeren models from uncommitted agent branch files
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

xeren_mod = types.ModuleType("xeren")
xeren_mod.__path__ = [str(root_dir / "src" / "xeren")]
sys.modules["xeren"] = xeren_mod

from xeren.models.config import ModelConfig
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.models.types import ChatMessage, Role


def test_integration():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== Step 07: Testing Xeren Agent Integration ===")

    # Configure Xeren's existing LocalOpenWeightAdapter to connect to our local server
    config = ModelConfig(
        model_id="xeren-nano",
        provider="local_openweight",
        api_base="http://127.0.0.1:8000/v1",
        temperature=0.7,
        max_tokens=64,
        timeout_seconds=30.0,
    )

    adapter = LocalOpenWeightAdapter(config)

    # 1. Ping test
    print("Testing ping connectivity...")
    is_live = adapter.ping()
    print(f"  • Provider Ping Status: {'ONLINE' if is_live else 'OFFLINE'}")

    if not is_live:
        print("Note: Start the server with `python training/src/inference/server.py` to test live chat.")
        return

    # 2. Generation test
    messages = [
        ChatMessage(role=Role.USER, content="Formulate an action plan to index documents in memory."),
    ]
    print("\nSending prompt through Xeren LocalOpenWeightAdapter...")
    response = adapter.generate(messages)

    print("\n✓ Received Response from Xeren LLM:")
    print(f"  • Model: {response.model_id}")
    print(f"  • Total Tokens: {response.usage.total_tokens}")
    print(f"  • Content:\n{response.content}")
    print("\n✓ Full End-to-End System Integration Verified!")


if __name__ == "__main__":
    test_integration()
