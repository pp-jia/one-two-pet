/**
 * one-two-pet — DSH host half.
 *
 * Installs the yier-hd pet pack into dsh-pet's user pet directory and serves a
 * small same-origin settings page at /one-two-pet/settings.  The client half
 * (plugin/client.js) only mounts that page as a settings.section iframe.
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

export const name = 'one-two-pet';
export const inject = ['webServer'];

const VERSION = '1.0.0';
const PACK = 'yier-hd';
const PREFIX = '/one-two-pet';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DISPLAYS = new Set(['web', 'desktop', 'both', 'none']);
const CORNERS = new Set(['top-left', 'top-right', 'bottom-left', 'bottom-right']);

function dshHome() {
  return process.env.DSH_HOME && process.env.DSH_HOME.trim() ? process.env.DSH_HOME : join(homedir(), '.dsh');
}

function petDir() {
  return join(dshHome(), 'dsh-pet', 'pet');
}

function configPath() {
  return join(petDir(), `${PACK}-config.json`);
}

function defaultConfig() {
  return JSON.parse(readFileSync(join(ROOT, 'pet', `${PACK}-config.json`), 'utf8'));
}

function installPack() {
  const dshPetRoot = join(dshHome(), 'dsh-pet');
  const target = petDir();
  mkdirSync(target, { recursive: true });

  const animSrc = join(ROOT, 'pet', `${PACK}-animation`);
  const animDst = join(target, `${PACK}-animation`);
  let copied = 0;
  if (existsSync(animSrc)) {
    mkdirSync(animDst, { recursive: true });
    for (const file of readdirSync(animSrc)) {
      if (!file.endsWith('.webm')) continue;
      copyFileSync(join(animSrc, file), join(animDst, file));
      copied += 1;
    }
  }

  // Never overwrite an existing user config: the settings page edits it.
  const cfgSrc = join(ROOT, 'pet', `${PACK}-config.json`);
  const cfgDst = configPath();
  if (!existsSync(cfgDst) && existsSync(cfgSrc)) copyFileSync(cfgSrc, cfgDst);
  writeFileSync(join(target, '.one-two-pet-version'), VERSION + '\n', 'utf8');

  return { dshPet: existsSync(dshPetRoot), petDir: target, copied };
}

function readConfig() {
  try {
    return JSON.parse(readFileSync(configPath(), 'utf8'));
  } catch {
    return defaultConfig();
  }
}

function validateConfig(cfg) {
  const pet = cfg && Array.isArray(cfg.pets) ? cfg.pets[0] : null;
  if (!pet || typeof pet !== 'object') throw new Error('config.pets[0] 缺失');
  if (!DISPLAYS.has(pet.display)) throw new Error('display 必须是 web/desktop/both/none');
  if (!Number.isFinite(Number(pet.size)) || Number(pet.size) < 120 || Number(pet.size) > 800) {
    throw new Error('size 必须在 120～800 之间');
  }
  const pos = pet.position && typeof pet.position === 'object' ? pet.position : {};
  if (!CORNERS.has(pos.corner)) throw new Error('position.corner 非法');
  if (!Number.isFinite(Number(pos.marginX)) || !Number.isFinite(Number(pos.marginY))) {
    throw new Error('position.marginX/marginY 必须是数字');
  }
  return cfg;
}

function patchConfig(patch) {
  const cfg = readConfig();
  const pet = cfg.pets[0];
  if (patch.display !== undefined) {
    if (!DISPLAYS.has(patch.display)) throw new Error('display 非法');
    pet.display = patch.display;
  }
  if (patch.size !== undefined) {
    const size = Number(patch.size);
    if (!Number.isFinite(size) || size < 120 || size > 800) throw new Error('size 必须在 120～800 之间');
    pet.size = size;
  }
  if (patch.corner !== undefined) {
    if (!CORNERS.has(patch.corner)) throw new Error('corner 非法');
    pet.position = { ...(pet.position || {}), corner: patch.corner };
  }
  if (patch.marginX !== undefined) {
    const v = Number(patch.marginX);
    if (!Number.isFinite(v)) throw new Error('marginX 非法');
    pet.position = { ...(pet.position || {}), marginX: v };
  }
  if (patch.marginY !== undefined) {
    const v = Number(patch.marginY);
    if (!Number.isFinite(v)) throw new Error('marginY 非法');
    pet.position = { ...(pet.position || {}), marginY: v };
  }
  validateConfig(cfg);
  writeFileSync(configPath(), JSON.stringify(cfg, null, 2) + '\n', 'utf8');
  return cfg;
}

function readBody(req, limit = 1 << 20) {
  return new Promise((resolveBody, reject) => {
    let data = '';
    let size = 0;
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      size += Buffer.byteLength(chunk);
      if (size > limit) {
        reject(new Error('body too large'));
        req.destroy();
        return;
      }
      data += chunk;
    });
    req.on('end', () => resolveBody(data));
    req.on('error', reject);
  });
}

function sendJson(res, status, obj) {
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
  });
  res.end(JSON.stringify(obj));
}

function sendHtml(res, body) {
  res.writeHead(200, {
    'content-type': 'text/html; charset=utf-8',
    'cache-control': 'no-store',
  });
  res.end(body);
}

function settingsHtml() {
  try {
    return readFileSync(join(ROOT, 'plugin', 'settings.html'), 'utf8');
  } catch {
    return '<!doctype html><meta charset="utf-8"><p>settings.html 缺失，请重装 one-two-pet。</p>';
  }
}

export function apply(ctx) {
  const installed = installPack();
  const log = (msg) => {
    try {
      ctx.logger?.info?.(msg);
    } catch {
      /* ignore */
    }
    console.log('[one-two-pet] ' + msg);
  };
  log(
    `pack ${VERSION} installed → ${installed.petDir}` +
      (installed.dshPet ? '' : '（未检测到 dsh-pet，需先安装 dsh-pet 才会显示）'),
  );

  async function reload(cfg) {
    const port = ctx.webServer?.port;
    if (!port) return { ok: false, reason: 'webServer 端口未就绪' };
    try {
      const r = await fetch(`http://127.0.0.1:${port}/dsh-pet-7340/pet-display`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ id: PACK, display: cfg.pets[0].display }),
      });
      const text = await r.text();
      let body = null;
      try {
        body = JSON.parse(text);
      } catch {
        /* ignore */
      }
      return { ok: r.ok && (body?.ok !== false), status: r.status, body };
    } catch (e) {
      return { ok: false, reason: e instanceof Error ? e.message : String(e) };
    }
  }

  const handler = async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const sub = url.pathname.slice(PREFIX.length).replace(/^\/+/, '').replace(/\/+$/, '');
    try {
      if (req.method === 'GET' && (sub === '' || sub === 'settings')) {
        sendHtml(res, settingsHtml());
        return;
      }
      if (req.method === 'GET' && sub === 'status') {
        sendJson(res, 200, {
          ok: true,
          version: VERSION,
          dshPet: existsSync(join(dshHome(), 'dsh-pet')),
          petDir: petDir(),
          config: readConfig(),
        });
        return;
      }
      if (req.method === 'GET' && sub === 'config') {
        sendJson(res, 200, { ok: true, config: readConfig() });
        return;
      }
      if (req.method === 'PUT' && sub === 'config') {
        let patch;
        try {
          patch = JSON.parse(await readBody(req));
        } catch (e) {
          sendJson(res, 400, { ok: false, reason: 'invalid JSON: ' + (e instanceof Error ? e.message : String(e)) });
          return;
        }
        try {
          const config = patchConfig(patch);
          sendJson(res, 200, { ok: true, config });
        } catch (e) {
          sendJson(res, 400, { ok: false, reason: e instanceof Error ? e.message : String(e) });
        }
        return;
      }
      if (req.method === 'POST' && sub === 'reload') {
        const cfg = readConfig();
        const result = await reload(cfg);
        sendJson(res, 200, { ok: true, reload: result, config: cfg });
        return;
      }
      sendJson(res, 404, { ok: false, reason: 'not found: ' + req.method + ' ' + url.pathname });
    } catch (e) {
      sendJson(res, 500, { ok: false, reason: e instanceof Error ? e.message : String(e) });
    }
  };

  if (ctx.effect) {
    ctx.effect(() => ctx.webServer.register({ kind: 'prefix', path: PREFIX, handler }), 'one-two-pet: routes');
  } else {
    ctx.webServer.register({ kind: 'prefix', path: PREFIX, handler });
  }
}
