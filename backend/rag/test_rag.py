import json
from search import search
from llm import analyze_root_cause, generate_repair_steps

print("=== SEARCH TEST ===")
results = search("CNC machine overheating bearing fault")
for r in results[:2]:
    print(f"  [sim={r['similarity']}] {r['content'][:120]}...")

print("\n=== ROOT CAUSE ANALYSIS ===")
diagnosis = analyze_root_cause("CNC-01", "CNC", "temperature", 97.4, "CRITICAL")
print(json.dumps(diagnosis, indent=2))

print("\n=== REPAIR STEPS ===")
repair = generate_repair_steps("CNC", "spindle bearing failure")
print(json.dumps(repair, indent=2))
