/**
 * GESTIMA FormTabs Component Tests
 *
 * Tests tab navigation, slots, icons, badges, and disabled states.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FormTabs from '../ui/FormTabs.vue'

describe('FormTabs Component', () => {
  // ==========================================================================
  // RENDERING - STRING TABS
  // ==========================================================================

  describe('Rendering - String Tabs', () => {
    const tabs = ['Tab 1', 'Tab 2', 'Tab 3']

    it('should render tab buttons', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons).toHaveLength(3)
      expect(buttons[0].text()).toBe('Tab 1')
      expect(buttons[1].text()).toBe('Tab 2')
      expect(buttons[2].text()).toBe('Tab 3')
    })

    it('should mark active tab', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 1,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].classes()).not.toContain('active')
      expect(buttons[1].classes()).toContain('active')
      expect(buttons[2].classes()).not.toContain('active')
    })

    it('should render tab content slots', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        },
        slots: {
          'tab-0': '<div class="content-0">Content 0</div>',
          'tab-1': '<div class="content-1">Content 1</div>',
          'tab-2': '<div class="content-2">Content 2</div>'
        }
      })

      expect(wrapper.find('.content-0').exists()).toBe(true)
      expect(wrapper.find('.content-1').exists()).toBe(true) // keepAlive=true (default)
      expect(wrapper.find('.content-2').exists()).toBe(true) // keepAlive=true (default)
    })
  })

  // ==========================================================================
  // RENDERING - OBJECT TABS
  // ==========================================================================

  describe('Rendering - Object Tabs', () => {
    const tabs = [
      { label: 'Basic', icon: '📝' },
      { label: 'Advanced', icon: '⚙️', badge: 5 },
      { label: 'Disabled', icon: '🔒', disabled: true }
    ]

    it('should render tab labels from objects', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].find('.tab-label').text()).toBe('Basic')
      expect(buttons[1].find('.tab-label').text()).toBe('Advanced')
      expect(buttons[2].find('.tab-label').text()).toBe('Disabled')
    })

    it('should render tab icons', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].find('.tab-icon').text()).toBe('📝')
      expect(buttons[1].find('.tab-icon').text()).toBe('⚙️')
      expect(buttons[2].find('.tab-icon').text()).toBe('🔒')
    })

    it('should render tab badges', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].find('.tab-badge').exists()).toBe(false)
      expect(buttons[1].find('.tab-badge').exists()).toBe(true)
      expect(buttons[1].find('.tab-badge').text()).toBe('5')
      expect(buttons[2].find('.tab-badge').exists()).toBe(false)
    })

    it('should disable tabs with disabled=true', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].attributes('disabled')).toBeUndefined()
      expect(buttons[1].attributes('disabled')).toBeUndefined()
      expect(buttons[2].attributes('disabled')).toBeDefined()
      expect(buttons[2].classes()).toContain('disabled')
    })
  })

  // ==========================================================================
  // TAB SWITCHING
  // ==========================================================================

  describe('Tab Switching', () => {
    const tabs = ['Tab 1', 'Tab 2', 'Tab 3']

    it('should emit update:modelValue on tab click', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      await buttons[1].trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([1])
    })

    it('should emit tab-change event', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      await buttons[1].trigger('click')

      expect(wrapper.emitted('tab-change')).toBeTruthy()
      expect(wrapper.emitted('tab-change')![0]).toEqual([1, 'Tab 2'])
    })

    it('should NOT emit events when clicking active tab', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      await buttons[0].trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
      expect(wrapper.emitted('tab-change')).toBeFalsy()
    })

    it('should NOT emit events when clicking disabled tab', async () => {
      const tabs = [
        { label: 'Tab 1' },
        { label: 'Tab 2', disabled: true }
      ]

      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      await buttons[1].trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
      expect(wrapper.emitted('tab-change')).toBeFalsy()
    })

    it('should switch visible content panel', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        },
        slots: {
          'tab-0': '<div class="content-0">Content 0</div>',
          'tab-1': '<div class="content-1">Content 1</div>',
          'tab-2': '<div class="content-2">Content 2</div>'
        }
      })

      expect(wrapper.find('.content-0').isVisible()).toBe(true)
      expect(wrapper.find('.content-1').exists()).toBe(true) // keepAlive=true (default)

      // Switch to tab 1
      await wrapper.setProps({ modelValue: 1 })

      const panels = wrapper.findAll('.tab-panel')
      expect(panels[1].classes()).toContain('active')
      expect(panels[0].classes()).not.toContain('active')
    })
  })

  // ==========================================================================
  // KEEP ALIVE
  // ==========================================================================

  describe('Keep Alive', () => {
    const tabs = ['Tab 1', 'Tab 2']

    it('should keep inactive tabs mounted when keepAlive=true', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs,
          keepAlive: true
        },
        slots: {
          'tab-0': '<div class="content-0">Content 0</div>',
          'tab-1': '<div class="content-1">Content 1</div>'
        }
      })

      // Switch to tab 1 to mount it
      await wrapper.setProps({ modelValue: 1 })
      expect(wrapper.find('.content-1').exists()).toBe(true)

      // Switch back to tab 0
      await wrapper.setProps({ modelValue: 0 })

      // Both should exist (keepAlive)
      expect(wrapper.find('.content-0').exists()).toBe(true)
      expect(wrapper.find('.content-1').exists()).toBe(true)
    })

    it('should NOT keep inactive tabs when keepAlive=false', async () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs,
          keepAlive: false
        },
        slots: {
          'tab-0': '<div class="content-0">Content 0</div>',
          'tab-1': '<div class="content-1">Content 1</div>'
        }
      })

      expect(wrapper.find('.content-0').exists()).toBe(true)
      expect(wrapper.find('.content-1').exists()).toBe(false)

      await wrapper.setProps({ modelValue: 1 })

      expect(wrapper.find('.content-0').exists()).toBe(false) // Unmounted
      expect(wrapper.find('.content-1').exists()).toBe(true)
    })
  })

  // ==========================================================================
  // VERTICAL MODE
  // ==========================================================================

  describe('Vertical Mode', () => {
    it('should apply vertical class', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs: ['Tab 1', 'Tab 2'],
          vertical: true
        }
      })

      expect(wrapper.find('.form-tabs').classes()).toContain('form-tabs-vertical')
    })
  })

  // ==========================================================================
  // ARIA ATTRIBUTES
  // ==========================================================================

  describe('ARIA Attributes', () => {
    const tabs = ['Tab 1', 'Tab 2']

    it('should set correct ARIA attributes on tabs', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        }
      })

      const buttons = wrapper.findAll('.tab-button')
      expect(buttons[0].attributes('role')).toBe('tab')
      expect(buttons[0].attributes('aria-selected')).toBe('true')
      expect(buttons[1].attributes('aria-selected')).toBe('false')
    })

    it('should set correct ARIA attributes on panels', () => {
      const wrapper = mount(FormTabs, {
        props: {
          modelValue: 0,
          tabs
        },
        slots: {
          'tab-0': '<div>Content 0</div>',
          'tab-1': '<div>Content 1</div>'
        }
      })

      const panels = wrapper.findAll('.tab-panel')
      expect(panels[0].attributes('role')).toBe('tabpanel')
      expect(panels[0].attributes('aria-hidden')).toBe('false')
    })
  })
})
