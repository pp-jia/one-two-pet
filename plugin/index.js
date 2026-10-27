/**
 * one-two-pet — DSH bundle that installs the yier-hd pet pack into dsh-pet.
 *
 * There is deliberately no settings page: the pet is configured through
 * %USERPROFILE%\.dsh\dsh-pet\pet\yier-hd-config.json (or the dsh-pet settings
 * page for main pets).  This package only makes distribution one-click:
 * install it, restart DSH, and the 5 HD clips + config are copied into place.
 */
import { copyFileSync, existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

export const name = 'one-two-pet';

const VERSION = '1.0.0';
const PACK = 'yier-hd';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

function dshHome() {
  return process.env.DSH_HOME && process.env.DSH_HOME.trim() ? process.env.DSH_HOME : join(homedir(), '.dsh');
}

function installPack() {
  const dshPetRoot = join(dshHome(), 'dsh-pet');
  const target = join(dshPetRoot, 'pet');
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

  // Never overwrite an existing user config: it is the pet's user-editable file.
  const cfgSrc = join(ROOT, 'pet', `${PACK}-config.json`);
  const cfgDst = join(target, `${PACK}-config.json`);
  if (!existsSync(cfgDst) && existsSync(cfgSrc)) copyFileSync(cfgSrc, cfgDst);
  writeFileSync(join(target, '.one-two-pet-version'), VERSION + '\n', 'utf8');

  return {
    dshPet: existsSync(join(dshPetRoot, 'main-config.jsonc')) || existsSync(join(dshPetRoot, 'logs.txt')),
    petDir: target,
    copied,
  };
}

export function apply(ctx) {
  const info = installPack();
  const message =
    `[one-two-pet] v${VERSION} installed ${info.copied} clips -> ${info.petDir}` +
    (info.dshPet ? '' : '（未检测到 dsh-pet；请先安装 dsh-pet，否则桌宠不会显示）');
  try {
    ctx?.logger?.info?.(message);
  } catch {
    /* ignore */
  }
  console.log(message);
}
