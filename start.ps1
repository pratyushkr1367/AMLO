$root = "C:\Users\OMEN\AMLO"

function Start-Service($title, $dir, $cmd) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "`$host.ui.RawUI.WindowTitle = '$title'; Set-Location '$dir'; $cmd"
    )
}

Write-Host "Starting AMLO stack..." -ForegroundColor Cyan

# ── Wave 1: Data pipeline + emulators ────────────────────────────────────────
Write-Host "[1/2] Starting data pipeline and emulators..." -ForegroundColor Yellow
Start-Service "AMLO | MQTT Bridge"   "$root\backend\data"                        "python mqtt_kafka_bridge.py"
Start-Service "AMLO | IoT Emulator"  "$root\backend\emulators\iot_emulator"      "python emulator.py"
Start-Service "AMLO | AGV Emulator"  "$root\backend\emulators\agv_emulator"      "python main.py"
Start-Sleep -Seconds 3

# ── Wave 2: Microservices + orchestration ─────────────────────────────────────
Write-Host "[2/3] Starting microservices and orchestration..." -ForegroundColor Yellow
Start-Service "AMLO | Asset Service"        "$root\backend\services\asset_service"        "python main.py"
Start-Service "AMLO | Inventory Service"    "$root\backend\services\inventory_service"    "python main.py"
Start-Service "AMLO | Work Order Service"   "$root\backend\services\work_order_service"   "python main.py"
Start-Service "AMLO | Logistics Service"    "$root\backend\services\logistics_service"    "python main.py"
Start-Service "AMLO | Notification Service" "$root\backend\services\notification_service" "python main.py"
Start-Service "AMLO | Sensor Service"       "$root\backend\services\sensor_service"       "python service.py"
Start-Service "AMLO | Anomaly Detector"     "$root\backend\dsa"                           "python anomaly_detector.py"
Start-Service "AMLO | Purchase Orders"      "$root\backend\services\purchase_order_service" "python main.py"
Start-Service "AMLO | Analytics"           "$root\backend\services\analytics_service"       "python main.py"
Start-Service "AMLO | Orchestration"       "$root\backend\agentic_orchestration"            "python runner.py"
Start-Sleep -Seconds 2

# ── Wave 3: Frontend ──────────────────────────────────────────────────────────
Write-Host "[3/3] Starting frontend..." -ForegroundColor Yellow
Start-Service "AMLO | Frontend"             "$root\frontend"                              "npm run dev"

Write-Host ""
Write-Host "All services launched." -ForegroundColor Green
Write-Host "  Frontend   : http://localhost:3000"
Write-Host "  AGV API    : http://localhost:8001"
Write-Host "  Asset API  : http://localhost:8002"
Write-Host "  Inventory  : http://localhost:8003"
Write-Host "  Work Orders: http://localhost:8004"
Write-Host "  Logistics  : http://localhost:8005"
Write-Host "  Notif/WS   : http://localhost:8006"
Write-Host "  Orch API   : http://localhost:8007"
Write-Host "  Purchase Orders: http://localhost:8008"
Write-Host "  Analytics  : http://localhost:8009"
