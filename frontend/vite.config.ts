import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    define: {
      'process.env.REACT_APP_BACKEND_URL': JSON.stringify(env.REACT_APP_BACKEND_URL || ''),
    },
    server: {
      port: 3000,
      host: '0.0.0.0',
      strictPort: false,
      cors: true,
      allowedHosts: [
        'pulse-sentinel-1.cluster-5.preview.emergentcf.cloud',
        'pulse-sentinel-1.preview.emergentagent.com',
        'sentinel-edge-live.preview.emergentagent.com',
        'localhost',
        '.preview.emergentcf.cloud',
        '.preview.emergentagent.com',
      ],
    },
    optimizeDeps: {
      include: ['zustand', 'framer-motion', 'lucide-react'],
    },
  };
});
