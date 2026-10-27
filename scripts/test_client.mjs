import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

let loaded = null;
globalThis.window = {
  __ModuleLoader__: {
    load(info) {
      loaded = info;
    },
  },
};
// eslint-disable-next-line no-eval
eval(readFileSync(resolve('plugin/client.js'), 'utf8'));
if (!loaded || loaded.id !== 'one-two-pet') throw new Error('client not loaded');

const mod = loaded.factory((name) => {
  if (name === 'react') {
    return { createElement: (type, props) => ({ type, props }) };
  }
  throw new Error('unexpected require: ' + name);
});
if (mod.name !== 'one-two-pet') throw new Error('bad client name');
if (!Array.isArray(mod.inject) || !mod.inject.includes('slots')) throw new Error('bad inject');

let registered = null;
const ctx = {
  slots: {
    inject(name, gen) {
      if (name !== 'settings.section') throw new Error('bad slot: ' + name);
      const it = gen();
      it.next();
    },
    register(opts, component) {
      registered = { opts, component };
      return { dispose() {} };
    },
  },
};
mod.apply(ctx);
if (!registered) throw new Error('section not registered');
if (registered.opts.id !== 'one-two-pet' || registered.opts.order !== 31) throw new Error('bad section opts');
if (registered.opts.label() !== '一二 HD') throw new Error('bad label');
const el = registered.component();
if (el.type !== 'iframe' || el.props.src !== '/one-two-pet/settings') throw new Error('bad iframe');
console.log('OK client', { id: registered.opts.id, label: registered.opts.label(), src: el.props.src });
