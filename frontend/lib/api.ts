import type { Machine, WorkOrder, InventoryItem, AGV, Technician } from './types'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export { fetcher }

export const API = {
  machines:    '/api/machines',
  inventory:   '/api/inventory',
  workOrders:  '/api/work-orders',
  technicians: '/api/technicians/available',
  agvs:        '/api/agvs',
}

export type { Machine, WorkOrder, InventoryItem, AGV, Technician }
