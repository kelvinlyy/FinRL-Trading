import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [
      { source: "/configure", destination: "/", permanent: false },
      { source: "/strategy", destination: "/", permanent: true },
      { source: "/overview", destination: "/", permanent: false },
    ];
  },
};

export default nextConfig;
