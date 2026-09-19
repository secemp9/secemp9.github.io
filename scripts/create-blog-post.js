// Shared desktop bridge. All post/metadata rules live in new_post_pelican.py.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);
const ROOT = path.resolve(__dirname, '..');

async function runAuthoring(args, root = ROOT) {
  const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!fs.existsSync(python)) {
    throw new Error('Set up .venv and install requirements.txt first; see the repository README.');
  }
  let stdout;
  try {
    ({ stdout } = await execFileAsync(python, [
      path.join(root, 'new_post_pelican.py'), ...args, '--json',
    ], { cwd: root, timeout: 30000, maxBuffer: 4 * 1024 * 1024, windowsHide: true }));
  } catch (error) {
    let result;
    try { result = JSON.parse(error.stdout || '{}'); } catch {}
    throw new Error(result?.error || error.stderr?.trim() || error.message);
  }
  const result = JSON.parse(stdout);
  if (result.error) throw new Error(result.error);
  return result;
}

const MIME = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp',
  '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.pdf': 'application/pdf', '.xml': 'application/xml; charset=utf-8',
};

async function startPreviewServer(directory, port = 4010) {
  const root = await fs.promises.realpath(directory);
  const server = http.createServer(async (request, response) => {
    if (!['GET', 'HEAD'].includes(request.method)) {
      response.writeHead(405, { Allow: 'GET, HEAD' }).end();
      return;
    }
    try {
      const url = new URL(request.url, 'http://localhost');
      const pathname = decodeURIComponent(url.pathname);
      const target = path.resolve(root, '.' + pathname, pathname.endsWith('/') ? 'index.html' : '');
      const relative = path.relative(root, target);
      if (relative.startsWith('..') || path.isAbsolute(relative)) {
        response.writeHead(403).end();
        return;
      }
      const real = await fs.promises.realpath(target);
      const realRelative = path.relative(root, real);
      if (realRelative.startsWith('..') || path.isAbsolute(realRelative)) {
        response.writeHead(403).end();
        return;
      }
      const body = await fs.promises.readFile(real);
      response.writeHead(200, {
        'Content-Type': MIME[path.extname(real).toLowerCase()] || 'application/octet-stream',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
      });
      response.end(request.method === 'HEAD' ? undefined : body);
    } catch (error) {
      response.writeHead(error instanceof URIError ? 400 : 404).end('Not found');
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  return server;
}

// Retain the old user-script entry point for existing personal templates.
// The checked-in vault now uses the Blog plugin, not automatic Templater events.
module.exports = async function createBlogPost(tp) {
  const title = await tp.system.prompt('Post title');
  if (!title?.trim()) return;
  const plan = await runAuthoring(['--prepare-post', '--title', title]);
  const file = await tp.app.vault.create(plan.path, plan.content);
  await tp.app.workspace.getLeaf('tab').openFile(file);
  return file;
};
module.exports.runAuthoring = runAuthoring;
module.exports.startPreviewServer = startPreviewServer;
