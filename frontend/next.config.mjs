/** @type {import('next').NextConfig} */

// バックエンド (FastAPI) の接続先。dev では同一オリジン扱いにするため
// /api/* を rewrite でプロキシし、CORS 設定をバックエンドに足さずに済ませる。
// 本番や別ホスト運用では BACKEND_ORIGIN 環境変数で差し替える。
const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig = {
  experimental: {
    optimizePackageImports: ["@phosphor-icons/react"],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
