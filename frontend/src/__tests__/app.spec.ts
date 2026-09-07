import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '../App.vue'
import { routes } from '../router'

async function mountApp(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] } })
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('App shell', () => {
  it('renders the three navigation tabs', async () => {
    const wrapper = await mountApp('/tasks')
    const text = wrapper.text()
    expect(text).toContain('Tasks')
    expect(text).toContain('Calendar')
    expect(text).toContain('Session')
  })

  it('redirects / to the tasks placeholder', async () => {
    const wrapper = await mountApp('/')
    expect(wrapper.text()).toContain('The task list lands in M2')
  })

  it('shows the calendar placeholder', async () => {
    const wrapper = await mountApp('/calendar')
    expect(wrapper.text()).toContain('Timeboxes land in M3')
  })
})
