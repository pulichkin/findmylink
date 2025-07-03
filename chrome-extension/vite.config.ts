import { defineConfig } from 'vite';
import { resolve } from 'path';
import fs from 'fs';
import path from 'path';

export default defineConfig({
  build: {
    outDir: 'dist',
    target: 'es2020',
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'src/popup.ts'),
        background: resolve(__dirname, 'src/background.ts'),
        "auth-page": resolve(__dirname, 'src/auth-page.ts'),
        "auth-widget": resolve(__dirname, 'src/auth-widget.ts')
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === 'style.css') return 'assets/popup.css';
          return 'assets/[name].[ext]';
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    postcss: './postcss.config.js'
  },
  plugins: [
    {
      name: 'copy-icons',
      closeBundle() {
        // Копируем иконки в dist/icons
        const iconsDir = resolve(__dirname, 'icons');
        const distIconsDir = resolve(__dirname, 'dist/icons');
        
        if (!fs.existsSync(distIconsDir)) {
          fs.mkdirSync(distIconsDir, { recursive: true });
        }
        
        if (fs.existsSync(iconsDir)) {
          const files = fs.readdirSync(iconsDir);
          files.forEach(file => {
            const sourcePath = path.join(iconsDir, file);
            const destPath = path.join(distIconsDir, file);
            fs.copyFileSync(sourcePath, destPath);
          });
        }
      }
    }
  ]
});
