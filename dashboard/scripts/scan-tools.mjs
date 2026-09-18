import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TOOLS_DIR = path.resolve(__dirname, '../../tools');
const OUTPUT_DATA_FILE = path.resolve(__dirname, '../src/data/tools-manifest.json');

const CATEGORY_META = {
  gaming: { label: '游戏娱乐', icon: '🎮', color: '#10b981' },
  finance: { label: '金融理财', icon: '📈', color: '#f59e0b' },
  study: { label: '学习辅助', icon: '📚', color: '#38bdf8' },
  productivity: { label: '生产力工具', icon: '⚡', color: '#a78bfa' },
  life: { label: '生活日常', icon: '☕', color: '#fb7185' },
};

function parseReadme(readmePath) {
  if (!fs.existsSync(readmePath)) return { title: '未命名工具', description: '' };
  const content = fs.readFileSync(readmePath, 'utf-8');
  const lines = content.split('\n');
  let title = '';
  let description = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('# ') && !title) {
      title = line.replace(/^#\s+/, '').trim();
    } else if (title && line && !line.startsWith('#') && !line.startsWith('-') && !line.startsWith('>') && !description) {
      description = line;
    }
    if (title && description) break;
  }

  return { title: title || '未命名工具', description: description || '暂无描述', rawContent: content };
}

function scan() {
  console.log('[Scanner] Scanning tools directory:', TOOLS_DIR);
  if (!fs.existsSync(TOOLS_DIR)) {
    console.warn('[Scanner] Tools directory not found!');
    return;
  }

  const categories = fs.readdirSync(TOOLS_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && !d.name.startsWith('.'));

  const toolsList = [];

  for (const catDir of categories) {
    const catName = catDir.name;
    const catPath = path.join(TOOLS_DIR, catName);
    const catMeta = CATEGORY_META[catName] || { label: catName, icon: '📦', color: '#6b7280' };

    const items = fs.readdirSync(catPath, { withFileTypes: true })
      .filter(d => d.isDirectory() && !d.name.startsWith('.'));

    for (const item of items) {
      const toolName = item.name;
      const toolPath = path.join(catPath, toolName);

      const readmePath = path.join(toolPath, 'README.md');
      const configExamplePath = path.join(toolPath, 'config.example.json');
      const configPath = path.join(toolPath, 'config.json');
      const outputPath = path.join(toolPath, 'output');

      const { title, description, rawContent } = parseReadme(readmePath);

      // Check config status
      let configKeys = [];
      if (fs.existsSync(configExamplePath)) {
        try {
          const cfg = JSON.parse(fs.readFileSync(configExamplePath, 'utf-8'));
          configKeys = Object.keys(cfg).filter(k => !k.startsWith('_'));
        } catch (e) {
          console.warn(`[Scanner] Error reading ${configExamplePath}:`, e.message);
        }
      }

      const isConfigured = fs.existsSync(configPath);

      // Check outputs
      let outputFiles = [];
      let latestDeals = null;

      if (fs.existsSync(outputPath)) {
        outputFiles = fs.readdirSync(outputPath).filter(f => f !== '.gitkeep');

        const latestJsonPath = path.join(outputPath, 'deals-latest.json');
        if (fs.existsSync(latestJsonPath)) {
          try {
            latestDeals = JSON.parse(fs.readFileSync(latestJsonPath, 'utf-8'));
          } catch (e) {
            console.warn(`[Scanner] Error reading deals-latest.json:`, e.message);
          }
        }
      }

      toolsList.push({
        id: `${catName}/${toolName}`,
        name: title,
        folderName: toolName,
        category: catName,
        categoryLabel: catMeta.label,
        categoryIcon: catMeta.icon,
        categoryColor: catMeta.color,
        description,
        readmeMarkdown: rawContent || '',
        configKeys,
        isConfigured,
        cliCommand: `python tools/${catName}/${toolName}/main.py`,
        outputFiles,
        hasOutputs: outputFiles.length > 0,
        latestDeals,
        updatedAt: new Date().toISOString()
      });
    }
  }

  const manifest = {
    scannedAt: new Date().toISOString(),
    totalTools: toolsList.length,
    categories: Object.keys(CATEGORY_META).map(k => ({
      key: k,
      ...CATEGORY_META[k],
      count: toolsList.filter(t => t.category === k).length
    })),
    tools: toolsList
  };

  const outDir = path.dirname(OUTPUT_DATA_FILE);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  fs.writeFileSync(OUTPUT_DATA_FILE, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`[Scanner] Successfully generated tools manifest with ${toolsList.length} tools to: ${OUTPUT_DATA_FILE}`);
  return manifest;
}

export { scan };

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  scan();
}
