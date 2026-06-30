"""
Orchestration Runner — Phase 7, AMLO

Consumes the Kafka 'alerts' topic and triggers the full agent graph
for every CRITICAL alert. Runs as its own process alongside the other services.

Fallback retry: when the LLM is rate-limited, the work order ID and state are
queued. A background thread retries every 5 minutes and patches the work order
with the real diagnosis once quota is available.

Run: python runner.py
"""

import json
import threading
import time

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer

from graph import run_orchestration
from triage import run_triage, is_fallback, FALLBACK_FAULT, _triage_cache

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
ALERTS_TOPIC            = "alerts"
WORK_ORDER_URL          = "http://127.0.0.1:8004"
RETRY_INTERVAL          = 60   # 1 minute

# Queue of {work_order_id, machine_id, machine_type, sensor_type, severity, average_value}
_retry_queue: list[dict] = []
_retry_lock  = threading.Lock()

# ── Mini HTTP server for manual retries ───────────────────────────────────────
api = FastAPI(title="AMLO Orchestration API")
api.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])


@api.get("/orchestration/llm-provider")
def get_llm_provider():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag"))
    from llm import get_provider
    from config import LLM_MODEL, LOCAL_LLM_MODEL
    return {"provider": get_provider(), "gemini_model": LLM_MODEL, "local_model": LOCAL_LLM_MODEL}


@api.post("/orchestration/llm-provider")
def set_llm_provider(body: dict):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag"))
    from llm import set_provider
    provider = body.get("provider", "")
    try:
        set_provider(provider)
        _triage_cache.clear()  # clear cache so next call uses new provider
        return {"provider": provider, "cache_cleared": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/orchestration/retry-queue")
def get_retry_queue():
    with _retry_lock:
        return [{"work_order_id": x["work_order_id"], "machine_id": x["machine_id"],
                 "machine_type": x["machine_type"], "sensor_type": x["sensor_type"]} for x in _retry_queue]


@api.post("/orchestration/retry/{wo_id}")
def manual_retry(wo_id: int):
    with _retry_lock:
        item = next((x for x in _retry_queue if x["work_order_id"] == wo_id), None)

    # If not in queue, reconstruct from DB on the fly
    if not item:
        try:
            wo = httpx.get(f"{WORK_ORDER_URL}/work-orders/{wo_id}", timeout=5.0).json()
            machines = httpx.get("http://127.0.0.1:8002/machines", timeout=5.0).json()
            machine  = next((m for m in machines if m["id"] == wo.get("machine_id")), {})
            item = {
                "work_order_id": wo_id,
                "machine_id":    machine.get("machine_id", ""),
                "machine_type":  machine.get("machine_type", ""),
                "sensor_type":   "",
                "severity":      "CRITICAL",
                "average_value": 0.0,
            }
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Could not load work order: {e}")

    try:
        result = run_triage(
            machine_type=item["machine_type"],
            sensor_type=item["sensor_type"],
            severity=item["severity"],
            machine_id=item["machine_id"],
            average_value=item["average_value"],
        )
        _patch_work_order(wo_id, result["diagnosis"], result["repair_steps"])
        with _retry_lock:
            if item in _retry_queue:
                _retry_queue.remove(item)
        return {"success": True, "diagnosis": result["diagnosis"].get("probable_cause")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _patch_work_order(wo_id: int, diagnosis: dict, repair: dict):
    description = (
        f"{diagnosis.get('probable_cause', 'Fault detected')}. "
        f"Confidence: {diagnosis.get('confidence', 'Unknown')}. "
        f"{diagnosis.get('recommended_action', '')}"
    )
    try:
        httpx.patch(
            f"{WORK_ORDER_URL}/work-orders/{wo_id}/diagnosis",
            json={
                "fault_type":  diagnosis.get("probable_cause", "Unknown"),
                "description": description,
                "parts_used":  repair.get("parts_needed", []),
            },
            timeout=5.0,
        )
        print(f"[RETRY] WO #{wo_id} patched with real diagnosis")
    except Exception as e:
        print(f"[RETRY] Failed to patch WO #{wo_id}: {e}")


def _retry_worker():
    while True:
        time.sleep(RETRY_INTERVAL)
        with _retry_lock:
            pending = list(_retry_queue)

        if not pending:
            continue

        print(f"[RETRY] Attempting LLM retry for {len(pending)} fallback work order(s)...")
        succeeded = []

        for item in pending:
            try:
                result = run_triage(
                    machine_type=item["machine_type"],
                    sensor_type=item["sensor_type"],
                    severity=item["severity"],
                    machine_id=item["machine_id"],
                    average_value=item["average_value"],
                )
                _patch_work_order(item["work_order_id"], result["diagnosis"], result["repair_steps"])
                succeeded.append(item)
                print(f"[RETRY] ✓ WO #{item['work_order_id']} — {result['diagnosis'].get('probable_cause')}")
            except Exception as e:
                print(f"[RETRY] ✗ WO #{item['work_order_id']} still failing: {e.__class__.__name__} — will retry")

        if succeeded:
            with _retry_lock:
                for item in succeeded:
                    _retry_queue.remove(item)
            print(f"[RETRY] {len(succeeded)} work order(s) updated — {len(_retry_queue)} still pending")


def _populate_retry_queue_from_db():
    """On startup, find all OPEN fallback work orders and add them to the retry queue."""
    try:
        wos = httpx.get(f"{WORK_ORDER_URL}/work-orders?status=OPEN", timeout=5.0).json()
        machines = httpx.get("http://127.0.0.1:8002/machines", timeout=5.0).json()
        machine_map = {m["id"]: m for m in machines}

        added = 0
        for wo in wos:
            if wo.get("fault_type") != FALLBACK_FAULT:
                continue
            machine = machine_map.get(wo.get("machine_id"), {})
            with _retry_lock:
                already = any(x["work_order_id"] == wo["id"] for x in _retry_queue)
            if not already:
                with _retry_lock:
                    _retry_queue.append({
                        "work_order_id": wo["id"],
                        "machine_id":    machine.get("machine_id", ""),
                        "machine_type":  machine.get("machine_type", ""),
                        "sensor_type":   "",   # not stored on old WOs — RAG still works
                        "severity":      "CRITICAL",
                        "average_value": 0.0,
                    })
                added += 1
        if added:
            print(f"[RETRY] Loaded {added} fallback work order(s) from DB into retry queue")
    except Exception as e:
        print(f"[RETRY] Could not populate queue from DB: {e}")


def _build_consumer():
    return KafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="orchestration-group",
        auto_offset_reset="latest",
        api_version=(3, 7, 0),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )


def main():
    print("Orchestration Runner started")
    print(f"  Topic   : {ALERTS_TOPIC}")
    print(f"  Triggers: CRITICAL severity only")
    print(f"  Retry   : fallback work orders retried every {RETRY_INTERVAL//60} min\n")

    threading.Thread(target=_retry_worker, daemon=True).start()
    threading.Thread(target=lambda: uvicorn.run(api, host="0.0.0.0", port=8007, log_level="warning"), daemon=True).start()
    threading.Thread(target=_populate_retry_queue_from_db, daemon=True).start()

    while True:
        try:
            consumer = _build_consumer()
            for message in consumer:
                event      = message.value
                severity   = event.get("severity", "")
                machine_id = event.get("machine_id", "")

                if severity != "CRITICAL":
                    print(f"[SKIP] {machine_id} | {severity}")
                    continue

                print(f"\n{'='*60}")
                print(f"[TRIGGER] {machine_id} | {event.get('sensor_type')} | CRITICAL")
                print(f"{'='*60}")

                try:
                    result = run_orchestration(event)
                    wo_id  = result.get("work_order_id")

                    print("\n[DONE] Pipeline complete:")
                    print(f"  Work Order  : #{wo_id}")
                    print(f"  AGV         : {result.get('agv_id')} dispatched ({len(result.get('agv_route') or [])} steps)")
                    t = result.get("technician")
                    print(f"  Technician  : {t.get('name') if t else 'None'}")
                    po = result.get("purchase_orders_created") or []
                    print(f"  POs created : {len(po)} ({', '.join(po) if po else 'none'})")

                    # Queue for retry if triage fell back to placeholder
                    diag = result.get("diagnosis") or {}
                    if wo_id and diag.get("probable_cause") == FALLBACK_FAULT:
                        with _retry_lock:
                            _retry_queue.append({
                                "work_order_id": wo_id,
                                "machine_id":    machine_id,
                                "machine_type":  event.get("machine_type", ""),
                                "sensor_type":   event.get("sensor_type", ""),
                                "severity":      severity,
                                "average_value": event.get("average_value", 0.0),
                            })
                        print(f"  [QUEUED] WO #{wo_id} for LLM retry (quota exceeded)")

                except Exception as e:
                    print(f"[ERROR] Orchestration failed: {e}")

        except ValueError as e:
            if "Invalid file descriptor" in str(e):
                print("[WARN] Kafka selector error — restarting consumer...")
                try:
                    consumer.close()
                except Exception:
                    pass
                continue
            raise


if __name__ == "__main__":
    main()
