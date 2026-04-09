import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: false,
    cors: true,
    allowedHosts: [
      'pulse-sentinel-1.cluster-5.preview.emergentcf.cloud',
      'pulse-sentinel-1.preview.emergentagent.com',
      'localhost',
      '.preview.emergentcf.cloud',
      '.preview.emergentagent.com',
    ],
  },
  optimizeDeps: {
    include: ['zustand', 'axios', 'framer-motion', 'lucide-react'],
  },
});
