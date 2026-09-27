import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ddgs import DDGS
from xeren.models import create_llm, ChatMessage

query = "what is gpt astra"
results = list(DDGS().text(query, max_results=3))
snippets = []
for r in results:
    body = r.get("body", "").strip()
    title = r.get("title", "").strip()
    if body:
        snippets.append(f"- **{title}**: {body}")

researched_text = "\n".join(snippets)

prompt = f"""You are Xeren, an autonomous AI reasoning and engineering system.
Answer the user's question with deep analytical insight, structured formatting, and practical takeaways.

### Researched Real-World Context:
{researched_text}

### User Question:
{query}

### Instructions for Response Structure:
1. **Conceptual Overview**: Explain clearly what this is in plain English, with a helpful analogy.
2. **Key Capabilities & Architecture**: Detail how it works using bullet points with emojis and technical specifics.
3. **Practical Comparison / Significance for Xeren**: Connect this concept to autonomous engineering, RAG, and private AI systems.
4. **Key Takeaways & Caveats**: Give a balanced, realistic conclusion.

Provide a thorough, articulate, multi-section response in clean Markdown. Do not output a short one-liner.

Answer:"""

print("Loading model and generating response...")
llm = create_llm(model_id="xeren_mini")
response = llm.generate([ChatMessage.user(prompt)])
print("\n" + "="*70)
print(response.content)
print("="*70)
