import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://askbiggie-a4fdf63d7e8b.herokuapp.com/api',
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'bignoodle.com',
        port: '',
        pathname: '/askbiggie/**',
      },
      {
        protocol: 'https',
        hostname: 'randomuser.me',
        port: '',
        pathname: '/api/portraits/**',
      },
    ],
  },
};

export default nextConfig;
