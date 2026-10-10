import vue from '@vitejs/plugin-vue'
import { defineConfig, type Plugin } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
// @ts-ignore
import { scan } from './scripts/scan-tools.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

import { spawn, execSync, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'

const runningProcesses = new Map<string, ChildProcess>()

function getPythonCommand(): string {
  const candidates = process.platform === 'win32' ? ['python', 'py', 'python3'] : ['python3', 'python']
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' })
      return cmd
    } catch {
      // try next
    }
  }
  return 'python'
}

function toolsWatcherPlugin(): Plugin {
  return {
    name: 'tools-watcher',
    configureServer(server) {
      const toolsPath = path.resolve(__dirname, '../tools')
      const rootDir = path.resolve(__dirname, '..')
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

      // 提供安全执行工具并以 SSE 流式回传实时日志的接口
      server.middlewares.use('/api/run-tool', (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.end('Method Not Allowed')
          return
        }

        let body = ''
        req.on('data', chunk => { body += chunk })
        req.on('end', () => {
          try {
            const { toolId, action, runId = Date.now().toString() } = JSON.parse(body || '{}')
            // 白名单路径安全校验：必须为 category/tool-name 格式，杜绝目录穿越
            if (!toolId || !/^[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+$/.test(toolId)) {
              res.statusCode = 400
              res.end(JSON.stringify({ success: false, error: '无效或非法的 toolId' }))
              return
            }

            const toolScript = path.resolve(rootDir, `tools/${toolId}/main.py`)
            if (!fs.existsSync(toolScript)) {
              res.statusCode = 404
              res.end(JSON.stringify({ success: false, error: `未找到工具入口文件: tools/${toolId}/main.py` }))
              return
            }

            // 建立 SSE 流式响应
            res.writeHead(200, {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache, no-transform',
              'Connection': 'keep-alive',
              'Access-Control-Allow-Origin': '*'
            })

            const pyCmd = getPythonCommand()
            const args = [`tools/${toolId}/main.py`]
            if (action && /^[a-zA-Z0-9_-]+$/.test(action)) {
              args.push(`--${action}`)
            }

            res.write(`data: ${JSON.stringify({ type: 'start', runId, command: `${pyCmd} ${args.join(' ')}` })}\n\n`)

            const child = spawn(pyCmd, args, {
              cwd: rootDir,
              env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                PYTHONIOENCODING: 'utf-8'
              },
              shell: false
            })

            runningProcesses.set(runId, child)

            child.stdout.on('data', (data) => {
              res.write(`data: ${JSON.stringify({ type: 'stdout', text: data.toString('utf-8') })}\n\n`)
            })

            child.stderr.on('data', (data) => {
              res.write(`data: ${JSON.stringify({ type: 'stderr', text: data.toString('utf-8') })}\n\n`)
            })

            child.on('close', (code) => {
              runningProcesses.delete(runId)
              res.write(`data: ${JSON.stringify({ type: 'exit', code: code ?? 0 })}\n\n`)
              res.end()
              // 运行结束后触发一次扫描，刷新产物
              debouncedScan()
            })

            child.on('error', (err) => {
              runningProcesses.delete(runId)
              res.write(`data: ${JSON.stringify({ type: 'error', text: err.message })}\n\n`)
              res.end()
            })

            res.on('close', () => {
              if (!res.writableEnded && runningProcesses.has(runId)) {
                try {
                  child.kill()
                } catch {}
                runningProcesses.delete(runId)
              }
            })
          } catch (e: any) {
            res.statusCode = 500
            res.end(JSON.stringify({ success: false, error: e.message }))
          }
        })
      })

      // 提供强行中止运行中的进程接口
      server.middlewares.use('/api/kill-tool', (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.end('Method Not Allowed')
          return
        }
        let body = ''
        req.on('data', chunk => { body += chunk })
        req.on('end', () => {
          try {
            const { runId } = JSON.parse(body || '{}')
            const proc = runningProcesses.get(runId)
            if (proc) {
              if (process.platform === 'win32' && proc.pid) {
                // Windows 下强行终止进程树
                spawn('taskkill', ['/pid', proc.pid.toString(), '/T', '/F'])
              } else {
                proc.kill('SIGTERM')
              }
              runningProcesses.delete(runId)
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ success: true, message: '进程已终止' }))
            } else {
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ success: true, message: '进程已结束或未找到' }))
            }
          } catch (e: any) {
            res.statusCode = 500
            res.end(JSON.stringify({ success: false, error: e.message }))
          }
        })
      })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), toolsWatcherPlugin()],
})

