import { mkdtempSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Readable } from 'node:stream';

const root = resolve(process.cwd());
const home = mkdtempSync(join(tmpdir(), 'one-two-pet-test-'));
process.env.DSH_HOME = home;

let handler = null;
const ctx = {
  webServer: {
    port: 0,
    register(opts) {
      handler = opts.handler;
      return () => {
        handler = null;
      };
    },
  },
  effect(fn) {
    return fn();
  },
  logger: { info() {} },
};

const mod = await import(pathToFileURL(join(root, 'plugin', 'index.js')).href);
if (mod.name !== 'one-two-pet') throw new Error('bad name');
mod.apply(ctx);
if (!handler) throw new Error('handler not registered');

function call(method, url, body) {
  return new Promise((resolveCall, reject) => {
    const req = Readable.from(body === undefined ? [] : [body]);
    req.method = method;
    req.url = url;
    const chunks = [];
    const res = {
      statusCode: 0,
      headers: null,
      writeHead(status, headers) {
        this.statusCode = status;
        this.headers = headers;
      },
      end(buf) {
        if (buf) chunks.push(Buffer.from(buf));
        resolveCall({
          status: this.statusCode,
          headers: this.headers,
          text: Buffer.concat(chunks).toString('utf8'),
        });
      },
      destroy() {},
    };
    handler(req, res).catch(reject);
  });
}

const status = await call('GET', '/one-two-pet/status');
const st = JSON.parse(status.text);
if (!st.ok || !st.config?.pets?.[0]) throw new Error('status failed: ' + status.text);
if (!existsSync(join(home, 'dsh-pet', 'pet', 'yier-hd-config.json'))) throw new Error('config not installed');
if (!existsSync(join(home, 'dsh-pet', 'pet', 'yier-hd-animation', '待机HD.webm'))) throw new Error('webm not installed');

const settings = await call('GET', '/one-two-pet/settings');
if (settings.status !== 200 || !settings.text.includes('一二 HD')) throw new Error('settings page failed');

const put = await call(
  'PUT',
  '/one-two-pet/config',
  JSON.stringify({ size: 320, display: 'web', corner: 'top-right', marginX: 30, marginY: 120 }),
);
const putJson = JSON.parse(put.text);
if (!putJson.ok) throw new Error('put failed: ' + put.text);
const cfg = putJson.config;
if (cfg.pets[0].size !== 320 || cfg.pets[0].position.corner !== 'top-right') throw new Error('patch not applied');
if (!Array.isArray(cfg.animations.clicks) || cfg.animations.clicks.length !== 4) throw new Error('animations lost');

const reload = await call('POST', '/one-two-pet/reload');
const reloadJson = JSON.parse(reload.text);
if (!reloadJson.ok) throw new Error('reload route failed: ' + reload.text);

const bad = await call('PUT', '/one-two-pet/config', JSON.stringify({ display: 'nope' }));
if (bad.status !== 400) throw new Error('invalid display accepted');

console.log('OK', { home, size: cfg.pets[0].size, clips: cfg.animations.clicks.length, reload: reloadJson.reload });
rmSync(home, { recursive: true, force: true });
