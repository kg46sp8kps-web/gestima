/**
 * GESTIMA Input Component Tests
 *
 * Tests v-model, label, placeholder, error/hint, types, disabled/readonly,
 * selectAll on click, editing states, and exposed methods.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Input from '../ui/Input.vue'

describe('Input Component', () => {
  // ==========================================================================
  // RENDERING - BASIC
  // ==========================================================================

  describe('Rendering - Basic', () => {
    it('should render input element', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.find('input').exists()).toBe(true)
      expect(wrapper.find('.input-wrapper').exists()).toBe(true)
    })

    it('should render label', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', label: 'Username' }
      })

      expect(wrapper.find('.input-label').text()).toBe('Username')
    })

    it('should render required asterisk', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', label: 'Email', required: true }
      })

      expect(wrapper.find('.input-required').exists()).toBe(true)
      expect(wrapper.find('.input-required').text()).toBe('*')
    })

    it('should render placeholder', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', placeholder: 'Enter text...' }
      })

      expect(wrapper.find('input').attributes('placeholder')).toBe('Enter text...')
    })

    it('should render with initial value', () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Hello' }
      })

      expect(wrapper.find('input').element.value).toBe('Hello')
    })
  })

  // ==========================================================================
  // V-MODEL
  // ==========================================================================

  describe('V-Model', () => {
    it('should emit update:modelValue on input', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      await wrapper.find('input').setValue('New value')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['New value'])
    })

    it('should emit number for type="number"', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 0, type: 'number' }
      })

      const input = wrapper.find('input')
      input.element.value = '42'
      await input.trigger('input')

      expect(wrapper.emitted('update:modelValue')![0]).toEqual([42])
    })

    it('should emit string for type="text"', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', type: 'text' }
      })

      await wrapper.find('input').setValue('123')

      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['123'])
    })
  })

  // ==========================================================================
  // INPUT TYPES
  // ==========================================================================

  describe('Input Types', () => {
    it('should default to type="text"', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.find('input').attributes('type')).toBe('text')
    })

    it('should accept type="number"', () => {
      const wrapper = mount(Input, {
        props: { modelValue: 0, type: 'number' }
      })

      expect(wrapper.find('input').attributes('type')).toBe('number')
    })

    it('should accept type="email"', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', type: 'email' }
      })

      expect(wrapper.find('input').attributes('type')).toBe('email')
    })

    it('should accept type="password"', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', type: 'password' }
      })

      expect(wrapper.find('input').attributes('type')).toBe('password')
    })
  })

  // ==========================================================================
  // DISABLED / READONLY
  // ==========================================================================

  describe('Disabled / Readonly', () => {
    it('should apply disabled attribute', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', disabled: true }
      })

      expect(wrapper.find('input').attributes('disabled')).toBeDefined()
      expect(wrapper.find('input').classes()).toContain('input-disabled')
    })

    it('should apply readonly attribute', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', readonly: true }
      })

      expect(wrapper.find('input').attributes('readonly')).toBeDefined()
    })

    it('should NOT select on click when disabled', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test', disabled: true }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      await wrapper.find('input').trigger('click')

      expect(selectSpy).not.toHaveBeenCalled()
    })

    it('should NOT select on click when readonly', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test', readonly: true }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      await wrapper.find('input').trigger('click')

      expect(selectSpy).not.toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // ERROR / HINT
  // ==========================================================================

  describe('Error / Hint', () => {
    it('should render error message', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', error: 'This field is required' }
      })

      expect(wrapper.find('.input-error').exists()).toBe(true)
      expect(wrapper.find('.input-error').text()).toBe('This field is required')
    })

    it('should apply error state class', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', error: 'Invalid' }
      })

      expect(wrapper.find('input').classes()).toContain('input-error-state')
    })

    it('should render hint message', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', hint: 'Enter at least 8 characters' }
      })

      expect(wrapper.find('.input-hint').exists()).toBe(true)
      expect(wrapper.find('.input-hint').text()).toBe('Enter at least 8 characters')
    })

    it('should prioritize error over hint', () => {
      const wrapper = mount(Input, {
        props: {
          modelValue: '',
          error: 'Error message',
          hint: 'Hint message'
        }
      })

      expect(wrapper.find('.input-error').exists()).toBe(true)
      expect(wrapper.find('.input-hint').exists()).toBe(false)
    })
  })

  // ==========================================================================
  // MONOSPACE
  // ==========================================================================

  describe('Monospace', () => {
    it('should apply mono class when mono=true', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', mono: true }
      })

      expect(wrapper.find('input').classes()).toContain('input-mono')
    })

    it('should NOT apply mono class by default', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.find('input').classes()).not.toContain('input-mono')
    })
  })

  // ==========================================================================
  // EDITING STATES (Collaborative)
  // ==========================================================================

  describe('Editing States', () => {
    it('should apply editing-self class', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', editingState: 'self' }
      })

      expect(wrapper.find('input').classes()).toContain('editing-self')
    })

    it('should apply editing-other class', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', editingState: 'other' }
      })

      expect(wrapper.find('input').classes()).toContain('editing-other')
    })

    it('should NOT apply editing class when null', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '', editingState: null }
      })

      expect(wrapper.find('input').classes()).not.toContain('editing-self')
      expect(wrapper.find('input').classes()).not.toContain('editing-other')
    })
  })

  // ==========================================================================
  // SELECT ALL ON CLICK (GESTIMA SPEC)
  // ==========================================================================

  describe('Select All on Click', () => {
    it('should select all text on click', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test value' }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      await wrapper.find('input').trigger('click')

      expect(selectSpy).toHaveBeenCalledTimes(1)
    })

    it('should NOT select when disabled', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test', disabled: true }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      await wrapper.find('input').trigger('click')

      expect(selectSpy).not.toHaveBeenCalled()
    })

    it('should NOT select when readonly', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test', readonly: true }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      await wrapper.find('input').trigger('click')

      expect(selectSpy).not.toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // FOCUS / BLUR EVENTS
  // ==========================================================================

  describe('Focus / Blur Events', () => {
    it('should emit focus event', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      await wrapper.find('input').trigger('focus')

      expect(wrapper.emitted('focus')).toBeTruthy()
      expect(wrapper.emitted('focus')).toHaveLength(1)
    })

    it('should emit blur event', async () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      await wrapper.find('input').trigger('blur')

      expect(wrapper.emitted('blur')).toBeTruthy()
      expect(wrapper.emitted('blur')).toHaveLength(1)
    })
  })

  // ==========================================================================
  // EXPOSED METHODS (defineExpose)
  // ==========================================================================

  describe('Exposed Methods', () => {
    it('should expose focus() method', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.vm.focus).toBeDefined()
      expect(typeof wrapper.vm.focus).toBe('function')
    })

    it('should expose blur() method', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.vm.blur).toBeDefined()
      expect(typeof wrapper.vm.blur).toBe('function')
    })

    it('should expose select() method', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      expect(wrapper.vm.select).toBeDefined()
      expect(typeof wrapper.vm.select).toBe('function')
    })

    it('should call input.focus() via exposed method', () => {
      const wrapper = mount(Input, {
        props: { modelValue: '' }
      })

      const focusSpy = vi.spyOn(wrapper.find('input').element, 'focus')
      wrapper.vm.focus()

      expect(focusSpy).toHaveBeenCalledTimes(1)
    })

    it('should call input.select() via exposed method', () => {
      const wrapper = mount(Input, {
        props: { modelValue: 'Test' }
      })

      const selectSpy = vi.spyOn(wrapper.find('input').element, 'select')
      wrapper.vm.select()

      expect(selectSpy).toHaveBeenCalledTimes(1)
    })
  })
})
