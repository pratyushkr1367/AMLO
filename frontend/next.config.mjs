/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      { source: '/api/machines/:path*',    destination: 'http://localhost:8002/machines/:path*' },
      { source: '/api/inventory/:path*',   destination: 'http://localhost:8003/inventory/:path*' },
      { source: '/api/work-orders/:path*', destination: 'http://localhost:8004/work-orders/:path*' },
      { source: '/api/technicians/:path*', destination: 'http://localhost:8005/technicians/:path*' },
      { source: '/api/agvs/:path*',        destination: 'http://localhost:8001/agvs/:path*' },
      { source: '/api/alerts/:path*',      destination: 'http://localhost:8006/alerts/:path*' },
    ]
  },
}

export default nextConfig
