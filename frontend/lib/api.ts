import type { Machine, WorkOrder, InventoryItem, AGV, Technician, PurchaseOrder } from './types'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export { fetcher }

export const API = {
  machines:       '/api/machines',
  inventory:      '/api/inventory',
  workOrders:     '/api/work-orders',
  technicians:    '/api/technicians/available',
  agvs:           '/api/agvs',
  purchaseOrders: '/api/purchase-orders',
  analytics: {
    oee:        '/api/analytics/oee',
    downtime:   '/api/analytics/downtime',
    predictive: '/api/analytics/predictive',
    summary:    '/api/analytics/summary',
  },
}

export type { Machine, WorkOrder, InventoryItem, AGV, Technician, PurchaseOrder }
