/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_HOST || 'localhost'

const nextConfig = {
  async rewrites() {
    return [
      { source: '/api/machines/:path*',         destination: `http://${BACKEND}:8002/machines/:path*` },
      { source: '/api/inventory/:path*',         destination: `http://${BACKEND}:8003/inventory/:path*` },
      { source: '/api/work-orders/:path*',       destination: `http://${BACKEND}:8004/work-orders/:path*` },
      { source: '/api/technicians/:path*',       destination: `http://${BACKEND}:8005/technicians/:path*` },
      { source: '/api/agvs/:path*',              destination: `http://${BACKEND}:8001/agvs/:path*` },
      { source: '/api/alerts/:path*',            destination: `http://${BACKEND}:8006/alerts/:path*` },
      { source: '/api/purchase-orders/:path*',   destination: `http://${BACKEND}:8008/purchase-orders/:path*` },
      { source: '/api/purchase-orders',          destination: `http://${BACKEND}:8008/purchase-orders` },
      { source: '/api/orchestration/:path*',     destination: `http://${BACKEND}:8007/orchestration/:path*` },
      { source: '/api/analytics/:path*',         destination: `http://${BACKEND}:8009/analytics/:path*` },
    ]
  },
}

export default nextConfig
