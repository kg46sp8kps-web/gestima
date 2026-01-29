/**
 * GESTIMA Button Component Tests
 *
 * Tests button variants, sizes, disabled/loading states, and click events.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '../ui/Button.vue'

describe('Button Component', () => {
  // ==========================================================================
  // RENDERING - VARIANTS
  // ==========================================================================

  describe('Rendering - Variants', () => {
    it('should render primary variant by default', () => {
      const wrapper = mount(Button, {
        slots: { default: 'Click me' }
      })

      expect(wrapper.find('button').classes()).toContain('btn')
      expect(wrapper.find('button').classes()).toContain('btn-primary')
      expect(wrapper.text()).toBe('Click me')
    })

    it('should render secondary variant', () => {
      const wrapper = mount(Button, {
        props: { variant: 'secondary' },
        slots: { default: 'Secondary' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-secondary')
    })

    it('should render danger variant', () => {
      const wrapper = mount(Button, {
        props: { variant: 'danger' },
        slots: { default: 'Delete' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-danger')
    })

    it('should render ghost variant', () => {
      const wrapper = mount(Button, {
        props: { variant: 'ghost' },
        slots: { default: 'Ghost' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-ghost')
    })
  })

  // ==========================================================================
  // RENDERING - SIZES
  // ==========================================================================

  describe('Rendering - Sizes', () => {
    it('should render medium size by default', () => {
      const wrapper = mount(Button, {
        slots: { default: 'Button' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-md')
    })

    it('should render small size', () => {
      const wrapper = mount(Button, {
        props: { size: 'sm' },
        slots: { default: 'Small' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-sm')
    })

    it('should render large size', () => {
      const wrapper = mount(Button, {
        props: { size: 'lg' },
        slots: { default: 'Large' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-lg')
    })
  })

  // ==========================================================================
  // DISABLED STATE
  // ==========================================================================

  describe('Disabled State', () => {
    it('should apply disabled attribute', () => {
      const wrapper = mount(Button, {
        props: { disabled: true },
        slots: { default: 'Disabled' }
      })

      const button = wrapper.find('button')
      expect(button.attributes('disabled')).toBeDefined()
      // Note: Component uses :disabled attribute, not class
    })

    it('should NOT emit click when disabled', async () => {
      const wrapper = mount(Button, {
        props: { disabled: true },
        slots: { default: 'Disabled' }
      })

      await wrapper.find('button').trigger('click')

      expect(wrapper.emitted('click')).toBeFalsy()
    })
  })

  // ==========================================================================
  // LOADING STATE
  // ==========================================================================

  describe('Loading State', () => {
    it('should show spinner when loading', () => {
      const wrapper = mount(Button, {
        props: { loading: true },
        slots: { default: 'Save' }
      })

      expect(wrapper.find('.btn-spinner').exists()).toBe(true)
    })

    it('should apply loading class', () => {
      const wrapper = mount(Button, {
        props: { loading: true },
        slots: { default: 'Save' }
      })

      expect(wrapper.find('button').classes()).toContain('btn-loading')
    })

    it('should NOT emit click when loading', async () => {
      const wrapper = mount(Button, {
        props: { loading: true },
        slots: { default: 'Save' }
      })

      await wrapper.find('button').trigger('click')

      expect(wrapper.emitted('click')).toBeFalsy()
    })

    it('should hide spinner when not loading', () => {
      const wrapper = mount(Button, {
        props: { loading: false },
        slots: { default: 'Save' }
      })

      expect(wrapper.find('.btn-spinner').exists()).toBe(false)
    })
  })

  // ==========================================================================
  // CLICK EVENTS
  // ==========================================================================

  describe('Click Events', () => {
    it('should emit click event', async () => {
      const wrapper = mount(Button, {
        slots: { default: 'Click me' }
      })

      await wrapper.find('button').trigger('click')

      expect(wrapper.emitted('click')).toBeTruthy()
      expect(wrapper.emitted('click')).toHaveLength(1)
    })

    it('should pass event to click handler', async () => {
      const onClick = vi.fn()
      const wrapper = mount(Button, {
        props: { onClick },
        slots: { default: 'Click me' }
      })

      await wrapper.find('button').trigger('click')

      expect(onClick).toHaveBeenCalledTimes(1)
      expect(onClick).toHaveBeenCalledWith(expect.any(Event))
    })

    it('should work with multiple clicks', async () => {
      const wrapper = mount(Button, {
        slots: { default: 'Click me' }
      })

      await wrapper.find('button').trigger('click')
      await wrapper.find('button').trigger('click')
      await wrapper.find('button').trigger('click')

      expect(wrapper.emitted('click')).toHaveLength(3)
    })
  })

  // ==========================================================================
  // BUTTON TYPE
  // ==========================================================================

  describe('Button Type', () => {
    it('should default to type="button"', () => {
      const wrapper = mount(Button, {
        slots: { default: 'Button' }
      })

      expect(wrapper.find('button').attributes('type')).toBe('button')
    })

    it('should allow type="submit"', () => {
      const wrapper = mount(Button, {
        props: { type: 'submit' },
        slots: { default: 'Submit' }
      })

      expect(wrapper.find('button').attributes('type')).toBe('submit')
    })

    it('should allow type="reset"', () => {
      const wrapper = mount(Button, {
        props: { type: 'reset' },
        slots: { default: 'Reset' }
      })

      expect(wrapper.find('button').attributes('type')).toBe('reset')
    })
  })

  // ==========================================================================
  // COMBINED STATES
  // ==========================================================================

  describe('Combined States', () => {
    it('should apply both disabled and loading styles', () => {
      const wrapper = mount(Button, {
        props: { disabled: true, loading: true },
        slots: { default: 'Save' }
      })

      const button = wrapper.find('button')
      expect(button.classes()).toContain('btn-loading')
      expect(button.attributes('disabled')).toBeDefined()
      expect(wrapper.find('.btn-spinner').exists()).toBe(true)
    })

    it('should render danger + small correctly', () => {
      const wrapper = mount(Button, {
        props: { variant: 'danger', size: 'sm' },
        slots: { default: 'Delete' }
      })

      const button = wrapper.find('button')
      expect(button.classes()).toContain('btn-danger')
      expect(button.classes()).toContain('btn-sm')
    })

    it('should render ghost + large correctly', () => {
      const wrapper = mount(Button, {
        props: { variant: 'ghost', size: 'lg' },
        slots: { default: 'Cancel' }
      })

      const button = wrapper.find('button')
      expect(button.classes()).toContain('btn-ghost')
      expect(button.classes()).toContain('btn-lg')
    })
  })

  // ==========================================================================
  // SLOT CONTENT
  // ==========================================================================

  describe('Slot Content', () => {
    it('should render text content', () => {
      const wrapper = mount(Button, {
        slots: { default: 'Save Changes' }
      })

      expect(wrapper.text()).toContain('Save Changes')
    })

    it('should render HTML content', () => {
      const wrapper = mount(Button, {
        slots: { default: '<span class="icon">💾</span> Save' }
      })

      expect(wrapper.find('.icon').exists()).toBe(true)
      expect(wrapper.html()).toContain('💾')
    })

    it('should hide content when loading (spinner takes precedence)', () => {
      const wrapper = mount(Button, {
        props: { loading: true },
        slots: { default: 'Save' }
      })

      // Slot uses v-else - content NOT in DOM when loading
      expect(wrapper.text()).not.toContain('Save')
      expect(wrapper.find('.btn-spinner').exists()).toBe(true)
    })
  })
})
