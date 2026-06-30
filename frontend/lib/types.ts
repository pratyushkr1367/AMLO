export type MachineStatus = 'NORMAL' | 'DEGRADING' | 'CRITICAL' | 'OFFLINE'
export type WorkOrderStatus = 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface Machine {
  id: number
  machine_id: string
  name: string
  machine_type: string
  status: MachineStatus
  location_row: number
  location_col: number
  last_maintenance: string | null
}

export interface WorkOrder {
  id: number
  machine_id: number
  technician_id: number | null
  priority: Priority
  status: WorkOrderStatus
  fault_type: string | null
  description: string | null
  parts_used: unknown[]
  agv_route: unknown[]
  created_at: string
  completed_at: string | null
}

export interface InventoryItem {
  id: number
  part_number: string
  part_name: string
  quantity: number
  unit: string
  reorder_threshold: number
}

export interface AGV {
  id: string
  position: { row: number; col: number }
  status: string
  busy: boolean
}

export interface Technician {
  id: number
  name: string
  skills: string[]
  available: boolean
  location_row: number
  location_col: number
}

export type POStatus = 'OPEN' | 'PROCESSING' | 'COMPLETED'

export interface PurchaseOrder {
  id: number
  part_number: string
  part_name: string
  quantity_ordered: number
  quantity_at_order: number
  reorder_threshold: number
  max_stock: number
  status: POStatus
  created_at: string
  approved_at: string | null
  completed_at: string | null
}

export interface AlertPayload {
  sensor_type: string
  average_value: number
  severity: string
  window_size?: number
}

export interface LiveAlert {
  event_type: string
  actor?: string
  entity_type: string
  entity_id: string
  payload: AlertPayload
  timestamp: string
  id: string
}
