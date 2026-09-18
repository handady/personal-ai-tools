import vue from '@vitejs/plugin-vue'
import { defineConfig, type Plugin } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
// @ts-ignore
import { scan } from './scripts/scan-tools.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function toolsWatcherPlugin(): Plugin {
  return {
    name: 'tools-watcher',
    configureServer(server) {
      const toolsPath = path.resolve(__dirname, '../tools')
      server.watcher.add(toolsPath)

      let timer: any = null
      const debouncedScan = () => {
        clearTimeout(timer)
        timer = setTimeout(() => {
          try {
            console.log('[tools-watcher] 捕获到工具产物或配置变动，正在重新扫描...')
            scan()
          } catch (e) {
            console.error('[tools-watcher] 重新扫描失败:', e)
          }
        }, 500)
      }

      server.watcher.on('add', (file) => {
        if (file.includes('output') || file.includes('config') || file.endsWith('.md')) {
          debouncedScan()
        }
      })
      server.watcher.on('change', (file) => {
        if (file.includes('output') || file.includes('config') || file.endsWith('.md')) {
          debouncedScan()
        }
      })
      server.watcher.on('unlink', (file) => {
        if (file.includes('output') || file.includes('config') || file.endsWith('.md')) {
          debouncedScan()
        }
      })

      // 提供前端主动点击重新扫描并获取最新数据的接口
      server.middlewares.use('/api/rescan', (_req, res) => {
        try {
          const manifest = scan()
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ success: true, manifest }))
        } catch (e: any) {
          res.statusCode = 500
          res.end(JSON.stringify({ success: false, error: e.message }))
        }
      })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), toolsWatcherPlugin()],
})

