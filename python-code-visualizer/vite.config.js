const { defineConfig } = require('vite');
const react = require('@vitejs/plugin-react');

// https://vitejs.dev/config/
module.exports = defineConfig(async () => {
  const tailwindcss = await import('@tailwindcss/vite');
  return {
    plugins: [react(), tailwindcss.default()],
    resolve: {
      alias: {
        '@': '/src',
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/execute': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
    test: {
      environment: 'jsdom',
      setupFiles: './tests/setup.ts',
      coverage: {
        reporter: ['text', 'json', 'html'],
      },
    },
  };
});