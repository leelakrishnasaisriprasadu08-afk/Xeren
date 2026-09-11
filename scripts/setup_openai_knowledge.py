import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from xeren.core.runtime import XerenCore
from xeren.plugins.knowledge.plugin import KnowledgePlugin

async def main():
    print("Initializing XerenCore and KnowledgePlugin...")
    core = XerenCore()
    
    # Ensure knowledge plugin is active
    k_plugin = core.get_plugin("knowledge")
    if not k_plugin:
        k_plugin = KnowledgePlugin()
        core.register_plugin(k_plugin)
        
    print("Ingesting knowledge into RAG/CAG backend...")
    
    texts = [
        "OpenAI is an American artificial intelligence research organization founded in December 2015. It focuses on researching and developing safe and beneficial AI.",
        "OpenAI developed the GPT (Generative Pre-trained Transformer) series of large language models, including GPT-3, GPT-4, and the widely known ChatGPT application.",
        "OpenAI's products also include DALL-E, an AI system that creates realistic images and art from a description in natural language, and Sora, a text-to-video model.",
        "OpenAI has partnered closely with Microsoft, which has invested billions of dollars into the company and integrates OpenAI's models into its products like GitHub Copilot and Microsoft Copilot.",
        "The mission of OpenAI is to ensure that artificial general intelligence (AGI) benefits all of humanity. It transitioned from a non-profit to a capped-profit structure to raise capital."
    ]
    
    try:
        res = core.ingest_knowledge(
            texts=texts,
            source="manual_cag_setup"
        )
        print(f"Successfully ingested data! Result: {res.status}")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        
    # Also append to the alignment dataset for instant zero-latency grounded fallback
    jsonl_path = os.path.join(os.path.dirname(__file__), "..", "training", "data", "xeren_identity", "xeren_alignment_train.jsonl")
    try:
        import json
        entry = {
            "messages": [
                {"role": "system", "content": "You are Xeren, an autonomous reasoning and action AI system capable of multi-step planning, tool execution, retrieval-augmented generation, and precise problem solving."},
                {"role": "user", "content": "what is openai"},
                {"role": "assistant", "content": "OpenAI is an AI research organization known for developing the GPT language models (including ChatGPT) and DALL-E image generation models. It was founded in 2015 with a mission to ensure that artificial general intelligence (AGI) benefits all of humanity."}
            ]
        }
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write("\n" + json.dumps(entry) + "\n")
        print("Successfully appended to xeren_alignment_train.jsonl!")
    except Exception as e:
        print(f"Failed to append to jsonl: {e}")

if __name__ == "__main__":
    asyncio.run(main())
