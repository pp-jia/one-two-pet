/**
 * one-two-pet — DSH client half.
 *
 * Registers a "一二 HD" settings section.  The section is a same-origin iframe
 * served by the host half (/one-two-pet/settings); the iframe owns the form and
 * talks to /one-two-pet/config, so this file stays tiny and does not depend on
 * DSH primitives.
 */
(function () {
  if (typeof window === 'undefined' || !window.__ModuleLoader__) return;

  window.__ModuleLoader__.load({
    id: 'one-two-pet',
    factory: function (require) {
      var module = { exports: {} };
      var React = require('react');

      var name = 'one-two-pet';
      var inject = ['slots'];

      function SettingsFrame() {
        return React.createElement('iframe', {
          src: '/one-two-pet/settings',
          title: '一二 HD 配置',
          style: {
            width: '100%',
            height: '760px',
            border: '0',
            borderRadius: '12px',
            background: 'transparent',
            colorScheme: 'light',
          },
        });
      }

      function apply(ctx) {
        ctx.slots.inject('settings.section', function* () {
          yield ctx.slots.register(
            {
              name: 'settings.section',
              id: 'one-two-pet',
              order: 31,
              label: function () {
                return '一二 HD';
              },
            },
            SettingsFrame,
          );
        });
      }

      module.exports = { name: name, inject: inject, apply: apply };
      return module.exports;
    },
  });
})();
