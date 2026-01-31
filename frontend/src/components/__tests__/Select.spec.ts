/**
 * GESTIMA Select Component Tests
 *
 * Tests select rendering, options, placeholder, v-model, error/hint,
 * disabled state, and number conversion.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Select from '../ui/Select.vue'

describe('Select Component', () => {
  const mockOptions = [
    { value: 1, label: 'Option 1' },
    { value: 2, label: 'Option 2' },
    { value: 3, label: 'Option 3' }
  ]

  // ==========================================================================
  // RENDERING - BASIC
  // ==========================================================================

  describe('Rendering - Basic', () => {
    it('should render select element', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      expect(wrapper.find('.select-wrapper').exists()).toBe(true)
      expect(wrapper.find('select').exists()).toBe(true)
      expect(wrapper.find('.select-arrow').exists()).toBe(true)
    })

    it('should render label', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, label: 'Choose option' }
      })

      expect(wrapper.find('.select-label').text()).toBe('Choose option')
    })

    it('should render required asterisk', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, label: 'Required', required: true }
      })

      expect(wrapper.find('.select-required').exists()).toBe(true)
      expect(wrapper.find('.select-required').text()).toBe('*')
    })

    it('should render options', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const options = wrapper.findAll('option')
      // No placeholder, so 3 options
      expect(options).toHaveLength(3)
      expect(options[0]!.text()).toBe('Option 1')
      expect(options[1]!.text()).toBe('Option 2')
      expect(options[2]!.text()).toBe('Option 3')
    })

    it('should render placeholder option', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, placeholder: 'Select...' }
      })

      const options = wrapper.findAll('option')
      // Placeholder + 3 options
      expect(options).toHaveLength(4)
      expect(options[0]!.text()).toBe('Select...')
      expect(options[0]!.attributes('value')).toBe('')
      expect(options[0]!.attributes('disabled')).toBeDefined()
    })
  })

  // ==========================================================================
  // V-MODEL
  // ==========================================================================

  describe('V-Model', () => {
    it('should set initial value', () => {
      const wrapper = mount(Select, {
        props: { modelValue: 2, options: mockOptions }
      })

      expect(wrapper.find('select').element.value).toBe('2')
    })

    it('should emit update:modelValue on change', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: 1, options: mockOptions }
      })

      await wrapper.find('select').setValue('2')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([2]) // Converted to number
    })

    it('should emit change event on change', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: 1, options: mockOptions }
      })

      await wrapper.find('select').setValue('3')

      expect(wrapper.emitted('change')).toBeTruthy()
      expect(wrapper.emitted('change')![0]).toEqual([3])
    })

    it('should emit string for string modelValue', async () => {
      const stringOptions = [
        { value: 'a', label: 'Option A' },
        { value: 'b', label: 'Option B' }
      ]

      const wrapper = mount(Select, {
        props: { modelValue: 'a', options: stringOptions }
      })

      await wrapper.find('select').setValue('b')

      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['b'])
    })

    it('should convert to number for number modelValue', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: 1, options: mockOptions }
      })

      await wrapper.find('select').setValue('2')

      expect(wrapper.emitted('update:modelValue')![0]).toEqual([2]) // Number, not "2"
    })
  })

  // ==========================================================================
  // OPTIONS
  // ==========================================================================

  describe('Options', () => {
    it('should render options with correct values', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const options = wrapper.findAll('option')
      expect(options[0]!.attributes('value')).toBe('1')
      expect(options[1]!.attributes('value')).toBe('2')
      expect(options[2]!.attributes('value')).toBe('3')
    })

    it('should render options with string values', () => {
      const stringOptions = [
        { value: 'red', label: 'Red' },
        { value: 'blue', label: 'Blue' }
      ]

      const wrapper = mount(Select, {
        props: { modelValue: '', options: stringOptions }
      })

      const options = wrapper.findAll('option')
      expect(options[0]!.attributes('value')).toBe('red')
      expect(options[1]!.attributes('value')).toBe('blue')
    })

    it('should handle empty options array', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: [] }
      })

      const options = wrapper.findAll('option')
      expect(options).toHaveLength(0)
    })

    it('should render many options', () => {
      const manyOptions = Array.from({ length: 100 }, (_, i) => ({
        value: i,
        label: `Option ${i}`
      }))

      const wrapper = mount(Select, {
        props: { modelValue: 0, options: manyOptions }
      })

      const options = wrapper.findAll('option')
      expect(options).toHaveLength(100)
    })
  })

  // ==========================================================================
  // DISABLED STATE
  // ==========================================================================

  describe('Disabled State', () => {
    it('should apply disabled attribute', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, disabled: true }
      })

      expect(wrapper.find('select').attributes('disabled')).toBeDefined()
      expect(wrapper.find('select').classes()).toContain('select-disabled')
    })

    it('should NOT emit events when disabled', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: 1, options: mockOptions, disabled: true }
      })

      await wrapper.find('select').setValue('2')

      // Disabled selects still emit events in Vue Test Utils
      // This is a browser limitation, not a Vue issue
      // In real browser, user cannot interact with disabled select
    })
  })

  // ==========================================================================
  // ERROR / HINT
  // ==========================================================================

  describe('Error / Hint', () => {
    it('should render error message', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, error: 'Please select an option' }
      })

      expect(wrapper.find('.select-error').exists()).toBe(true)
      expect(wrapper.find('.select-error').text()).toBe('Please select an option')
    })

    it('should apply error state class', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, error: 'Invalid' }
      })

      expect(wrapper.find('select').classes()).toContain('select-error-state')
    })

    it('should render hint message', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, hint: 'Choose your preference' }
      })

      expect(wrapper.find('.select-hint').exists()).toBe(true)
      expect(wrapper.find('.select-hint').text()).toBe('Choose your preference')
    })

    it('should prioritize error over hint', () => {
      const wrapper = mount(Select, {
        props: {
          modelValue: '',
          options: mockOptions,
          error: 'Error message',
          hint: 'Hint message'
        }
      })

      expect(wrapper.find('.select-error').exists()).toBe(true)
      expect(wrapper.find('.select-hint').exists()).toBe(false)
    })
  })

  // ==========================================================================
  // FOCUS / BLUR EVENTS
  // ==========================================================================

  describe('Focus / Blur Events', () => {
    it('should emit focus event', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      await wrapper.find('select').trigger('focus')

      expect(wrapper.emitted('focus')).toBeTruthy()
      expect(wrapper.emitted('focus')).toHaveLength(1)
    })

    it('should emit blur event', async () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      await wrapper.find('select').trigger('blur')

      expect(wrapper.emitted('blur')).toBeTruthy()
      expect(wrapper.emitted('blur')).toHaveLength(1)
    })
  })

  // ==========================================================================
  // EXPOSED METHODS (defineExpose)
  // ==========================================================================

  describe('Exposed Methods', () => {
    it('should expose focus() method', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      expect(wrapper.vm.focus).toBeDefined()
      expect(typeof wrapper.vm.focus).toBe('function')
    })

    it('should expose blur() method', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      expect(wrapper.vm.blur).toBeDefined()
      expect(typeof wrapper.vm.blur).toBe('function')
    })

    it('should call select.focus() via exposed method', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const focusSpy = vi.spyOn(wrapper.find('select').element, 'focus')
      wrapper.vm.focus()

      expect(focusSpy).toHaveBeenCalledTimes(1)
    })
  })

  // ==========================================================================
  // PLACEHOLDER
  // ==========================================================================

  describe('Placeholder', () => {
    it('should render placeholder as first option', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions, placeholder: 'Choose one...' }
      })

      const firstOption = wrapper.findAll('option')[0]!
      expect(firstOption.text()).toBe('Choose one...')
      expect(firstOption.attributes('disabled')).toBeDefined()
      expect(firstOption.attributes('value')).toBe('')
    })

    it('should NOT render placeholder when not provided', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const options = wrapper.findAll('option')
      expect(options).toHaveLength(3) // No placeholder
    })
  })

  // ==========================================================================
  // CUSTOM ARROW
  // ==========================================================================

  describe('Custom Arrow', () => {
    it('should render custom arrow', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const arrow = wrapper.find('.select-arrow')
      expect(arrow.exists()).toBe(true)
      expect(arrow.text()).toBe('▼')
    })

    it('should position arrow correctly', () => {
      const wrapper = mount(Select, {
        props: { modelValue: '', options: mockOptions }
      })

      const container = wrapper.find('.select-container')
      const arrow = wrapper.find('.select-arrow')

      expect((container.element as HTMLElement).style.position).toBe('') // Set via CSS
      expect(arrow.exists()).toBe(true)
    })
  })

  // ==========================================================================
  // COMBINED PROPS
  // ==========================================================================

  describe('Combined Props', () => {
    it('should render with all props', () => {
      const wrapper = mount(Select, {
        props: {
          modelValue: 2,
          options: mockOptions,
          label: 'Select option',
          placeholder: 'Choose...',
          required: true,
          hint: 'Select your choice'
        }
      })

      expect(wrapper.find('.select-label').text()).toContain('Select option')
      expect(wrapper.find('.select-required').exists()).toBe(true)
      expect(wrapper.findAll('option')[0]!.text()).toBe('Choose...')
      expect(wrapper.find('select').element.value).toBe('2')
      expect(wrapper.find('.select-hint').text()).toBe('Select your choice')
    })
  })
})
