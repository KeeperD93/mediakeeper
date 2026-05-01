/**
 * Global test setup — stubs vue-i18n + vue-router so components that
 * use $t()/useI18n() or useRouter() do not crash in isolated tests.
 */
import { config } from '@vue/test-utils'

config.global.mocks = {
  $t: (key, params) => {
    if (params && typeof params === 'object') return `${key}:${JSON.stringify(params)}`
    return key
  },
  $tc: key => key,
}

config.global.stubs = {
  // Teleport content is verified in isolation — no real DOM insertion needed.
  Teleport: { template: '<div><slot /></div>' },
  transition: { template: '<div><slot /></div>' },
  'router-link': { template: '<a><slot /></a>' },
}
