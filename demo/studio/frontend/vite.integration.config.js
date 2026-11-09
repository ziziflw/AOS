import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({base:'./',plugins:[vue()],build:{outDir:'../../../apps/aos-workbench/dist-integrated',rollupOptions:{input:'integration.html'}}})
