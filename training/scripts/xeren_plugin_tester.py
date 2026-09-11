import asyncio
import json
from xeren.core.runtime import XerenCore
from xeren.models import create_llm

async def run_tests():
    core = XerenCore(auto_register_defaults=True)
    # Ensure native model is loaded
    core.llm = create_llm(model_id="xeren_mini")
    core.set_llm(core.llm)

    test_cases = [
        "what is your name?",
        "where are you from?",
        "what is the capital of india?",
        "how many states are in india?",
        "write a python function to add two numbers",
        "create a 3d website for digital gold",
        "scrape the latest news on AI",
        "list the files in the workspace",
        "who created you?",
        "solve 2x + 5 = 15"
    ]

    print("Starting XerenCore Native Verification Tests...\n")
    results = []

    for idx, query in enumerate(test_cases, 1):
        print(f"[{idx}/{len(test_cases)}] Testing: '{query}'")
        try:
            res = await core.aprocess_request(query, verify_outcome=True)
            results.append({
                "query": query,
                "status": "success",
                "final_response": res.get("final_response")
            })
            print(f"  -> Success. Response length: {len(str(res.get('final_response')))}")
        except Exception as e:
            results.append({
                "query": query,
                "status": "error",
                "error": str(e)
            })
            print(f"  -> Failed: {e}")

    with open("test_report.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nTests completed. Report saved to test_report.json")

if __name__ == "__main__":
    asyncio.run(run_tests())
