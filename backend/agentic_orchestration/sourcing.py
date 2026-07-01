"""
Sourcing Agent — Phase 7, AMLO

Node 2 of the orchestration graph.
For each part in the repair plan:
  - Checks stock via the Inventory Service
  - If stock = 0, creates a purchase order in MongoDB
"""

from datetime import datetime, timezone

import httpx
from pymongo import MongoClient

from state import OrchestratorState

INVENTORY_URL = "http://127.0.0.1:8003"
MONGO_URI = "mongodb://127.0.0.1:27017"


def sourcing_node(state: OrchestratorState) -> dict:
    parts_needed = (state.get("repair_steps") or {}).get("parts_needed", [])
    print(f"\n[SOURCING] Checking {len(parts_needed)} parts for {state['machine_id']}")

    parts_status: list = []
    purchase_orders_created: list = []

    mongo = MongoClient(MONGO_URI)
    db = mongo["amlo_db"]

    for part in parts_needed:
        part_number = part.get("part_number", "")

        if part_number in ("N/A", ""):
            parts_status.append({**part, "available": True, "stock": "consumable"})
            continue

        try:
            resp = httpx.get(f"{INVENTORY_URL}/inventory/{part_number}", timeout=5.0)
            if resp.status_code == 200:
                stock = resp.json().get("quantity_in_stock", 0)
                if stock > 0:
                    parts_status.append({**part, "available": True, "stock": stock})
                    print(f"  [OK]  {part_number}: {stock} in stock")
                else:
                    parts_status.append({**part, "available": False, "stock": 0})
                    db.purchase_orders.insert_one({
                        "part_number": part_number,
                        "part_name": part.get("part_name", ""),
                        "quantity_ordered": part.get("quantity", 1),
                        "supplier": "AutoParts Ltd",
                        "status": "pending",
                        "machine_id": state["machine_id"],
                        "created_at": datetime.now(timezone.utc),
                    })
                    purchase_orders_created.append(part_number)
                    print(f"  [PO]  {part_number}: out of stock → purchase order created")
            else:
                parts_status.append({**part, "available": False, "stock": "not_found"})
                print(f"  [?]   {part_number}: not in inventory (HTTP {resp.status_code})")
        except Exception as e:
            parts_status.append({**part, "available": False, "stock": "error"})
            print(f"  [ERR] {part_number}: {e}")

    mongo.close()
    return {"parts_status": parts_status, "purchase_orders_created": purchase_orders_created}
