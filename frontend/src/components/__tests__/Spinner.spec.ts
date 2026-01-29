/**
 * GESTIMA Spinner Component Tests
 *
 * Tests spinner rendering, size, text, and inline mode.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Spinner from '../ui/Spinner.vue'

describe('Spinner Component', () => {
  // ==========================================================================
  // RENDERING - BASIC
  // ==========================================================================

  describe('Rendering - Basic', () => {
    it('should render spinner element', () => {
      const wrapper = mount(Spinner)

      expect(wrapper.find('.spinner-container').exists()).toBe(true)
      expect(wrapper.find('.spinner').exists()).toBe(true)
    })

    it('should use default size 24px', () => {
      const wrapper = mount(Spinner)

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 24px')
      expect(spinner.attributes('style')).toContain('height: 24px')
    })

    it('should render without text by default', () => {
      const wrapper = mount(Spinner)

      expect(wrapper.find('.spinner-text').exists()).toBe(false)
    })

    it('should NOT have inline class by default', () => {
      const wrapper = mount(Spinner)

      expect(wrapper.find('.spinner-container').classes()).not.toContain('inline')
    })
  })

  // ==========================================================================
  // SIZE
  // ==========================================================================

  describe('Size', () => {
    it('should apply custom size in pixels', () => {
      const wrapper = mount(Spinner, {
        props: { size: '48px' }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 48px')
      expect(spinner.attributes('style')).toContain('height: 48px')
    })

    it('should apply custom size in rem', () => {
      const wrapper = mount(Spinner, {
        props: { size: '2rem' }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 2rem')
      expect(spinner.attributes('style')).toContain('height: 2rem')
    })

    it('should apply small size', () => {
      const wrapper = mount(Spinner, {
        props: { size: '16px' }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 16px')
      expect(spinner.attributes('style')).toContain('height: 16px')
    })

    it('should apply large size', () => {
      const wrapper = mount(Spinner, {
        props: { size: '64px' }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 64px')
      expect(spinner.attributes('style')).toContain('height: 64px')
    })
  })

  // ==========================================================================
  // TEXT
  // ==========================================================================

  describe('Text', () => {
    it('should render text prop', () => {
      const wrapper = mount(Spinner, {
        props: { text: 'Loading...' }
      })

      expect(wrapper.find('.spinner-text').exists()).toBe(true)
      expect(wrapper.find('.spinner-text').text()).toBe('Loading...')
    })

    it('should render custom text', () => {
      const wrapper = mount(Spinner, {
        props: { text: 'Please wait' }
      })

      expect(wrapper.find('.spinner-text').text()).toBe('Please wait')
    })

    it('should NOT render text when empty string', () => {
      const wrapper = mount(Spinner, {
        props: { text: '' }
      })

      expect(wrapper.find('.spinner-text').exists()).toBe(false)
    })

    it('should render with both size and text', () => {
      const wrapper = mount(Spinner, {
        props: { size: '32px', text: 'Loading data...' }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 32px')
      expect(wrapper.find('.spinner-text').text()).toBe('Loading data...')
    })
  })

  // ==========================================================================
  // INLINE MODE
  // ==========================================================================

  describe('Inline Mode', () => {
    it('should apply inline class when inline=true', () => {
      const wrapper = mount(Spinner, {
        props: { inline: true }
      })

      expect(wrapper.find('.spinner-container').classes()).toContain('inline')
    })

    it('should NOT apply inline class when inline=false', () => {
      const wrapper = mount(Spinner, {
        props: { inline: false }
      })

      expect(wrapper.find('.spinner-container').classes()).not.toContain('inline')
    })

    it('should render inline with text', () => {
      const wrapper = mount(Spinner, {
        props: { inline: true, text: 'Loading...' }
      })

      expect(wrapper.find('.spinner-container').classes()).toContain('inline')
      expect(wrapper.find('.spinner-text').exists()).toBe(true)
    })
  })

  // ==========================================================================
  // COMBINED PROPS
  // ==========================================================================

  describe('Combined Props', () => {
    it('should render with all props', () => {
      const wrapper = mount(Spinner, {
        props: {
          size: '40px',
          text: 'Processing...',
          inline: true
        }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 40px')
      expect(spinner.attributes('style')).toContain('height: 40px')
      expect(wrapper.find('.spinner-text').text()).toBe('Processing...')
      expect(wrapper.find('.spinner-container').classes()).toContain('inline')
    })

    it('should render large spinner with text', () => {
      const wrapper = mount(Spinner, {
        props: {
          size: '64px',
          text: 'Please wait...'
        }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 64px')
      expect(wrapper.find('.spinner-text').text()).toBe('Please wait...')
    })

    it('should render small inline spinner', () => {
      const wrapper = mount(Spinner, {
        props: {
          size: '16px',
          inline: true
        }
      })

      const spinner = wrapper.find('.spinner')
      expect(spinner.attributes('style')).toContain('width: 16px')
      expect(wrapper.find('.spinner-container').classes()).toContain('inline')
    })
  })

  // ==========================================================================
  // ANIMATION (CSS)
  // ==========================================================================

  describe('Animation', () => {
    it('should have spinner element for animation', () => {
      const wrapper = mount(Spinner)

      // Spinner should exist (animation defined in CSS)
      expect(wrapper.find('.spinner').exists()).toBe(true)
    })
  })
})
