import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const npm = fileURLToPath(new URL('./js-out/node_modules', import.meta.url));

export default defineConfig({
  resolve: {
    alias: [
      { find: /^melange\.js\/(.*)/, replacement: npm + '/melange.js/$1' },
      { find: /^melange\.belt\/(.*)/, replacement: npm + '/melange.belt/$1' },
      { find: /^melange\/(.*)/, replacement: npm + '/melange/$1' },
      { find: /^react-dom\/client$/, replacement: npm + '/react-dom/index.js' },
      { find: /^react-dom\/(.*)/, replacement: npm + '/react-dom/$1.js' },
      { find: /^react\/(.*)/, replacement: npm + '/react/$1.js' },
      { find: 'react-dom', replacement: npm + '/react-dom/index.js' },
      { find: 'react', replacement: npm + '/react/index.js' },
    ],
  },
  build: { outDir: 'dist', emptyOutDir: true },
});
