/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    // Baked in at `next build` (i.e. on every frontend Docker build), shown in the chat footer
    NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
