import { mkdtempSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = resolve(process.cwd());
const home = mkdtempSync(join(tmpdir(), 'one-two-pet-test-'));
process.env.DSH_HOME = home;

const mod = await import(pathToFileURL(join(root, 'plugin', 'index.js')).href);
if (mod.name !== 'one-two-pet') throw new Error('bad name');
mod.apply({ logger: { info() {} } });

const cfgPath = join(home, 'dsh-pet', 'pet', 'yier-hd-config.json');
const animDir = join(home, 'dsh-pet', 'pet', 'yier-hd-animation');
if (!existsSync(cfgPath)) throw new Error('config not installed');
for (const name of ['待机HD', '荡秋千HD', '脑阔疼HD', '拜托球球你HD', '护肤HD']) {
  if (!existsSync(join(animDir, `${name}.webm`))) throw new Error(`missing ${name}.webm`);
}
const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
if (cfg.pets[0].id !== 'yier-hd') throw new Error('bad config id');
if (!Array.isArray(cfg.animations.clicks) || cfg.animations.clicks.length !== 4) throw new Error('bad clips');

console.log('OK', { home, clips: cfg.animations.clicks.length, files: 5 });
rmSync(home, { recursive: true, force: true });
