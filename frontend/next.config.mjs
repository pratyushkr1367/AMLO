/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      { source: '/api/machines/:path*',    destination: 'http://localhost:8002/machines/:path*' },
      { source: '/api/inventory/:path*',   destination: 'http://localhost:8003/inventory/:path*' },
      { source: '/api/work-orders/:path*', destination: 'http://localhost:8004/work-orders/:path*' },
      { source: '/api/technicians/:path*', destination: 'http://localhost:8005/technicians/:path*' },
      { source: '/api/agvs/:path*',        destination: 'http://localhost:8001/agvs/:path*' },
      { source: '/api/alerts/:path*',        destination: 'http://localhost:8006/alerts/:path*' },
      { source: '/api/purchase-orders/:path*',  destination: 'http://localhost:8008/purchase-orders/:path*' },
      { source: '/api/purchase-orders',         destination: 'http://localhost:8008/purchase-orders' },
      { source: '/api/orchestration/:path*',    destination: 'http://localhost:8007/orchestration/:path*' },
      { source: '/api/analytics/:path*',        destination: 'http://localhost:8009/analytics/:path*' },
    ]
  },
}

export default nextConfig
