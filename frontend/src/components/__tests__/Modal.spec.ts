/**
 * GESTIMA Modal Component Tests
 *
 * Tests modal rendering, sizes, close events, backdrop click, ESC key,
 * slots, and body scroll lock.
 *
 * NOTE: Modal uses <Teleport to="body">, so we use document.querySelector
 * instead of wrapper.find() to test the rendered DOM.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Modal from '../ui/Modal.vue'

describe('Modal Component', () => {
  // Create mount point for Teleport
  let attachTarget: HTMLDivElement

  beforeEach(() => {
    document.body.style.overflow = ''
    attachTarget = document.createElement('div')
    document.body.appendChild(attachTarget)
  })

  afterEach(() => {
    document.body.style.overflow = ''
    document.body.innerHTML = '' // Clear all DOM including teleported content
  })

  // ==========================================================================
  // RENDERING - VISIBILITY
  // ==========================================================================

  describe('Rendering - Visibility', () => {
    it('should NOT render when modelValue=false', async () => {
      mount(Modal, {
        props: { modelValue: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-backdrop')).toBeFalsy()
      expect(document.querySelector('.modal')).toBeFalsy()
    })

    it('should render when modelValue=true', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-backdrop')).toBeTruthy()
      expect(document.querySelector('.modal')).toBeTruthy()
    })

    it('should render modal content', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Modal content here' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modalBody = document.querySelector('.modal-body')
      expect(modalBody?.textContent).toBe('Modal content here')
    })
  })

  // ==========================================================================
  // SIZES
  // ==========================================================================

  describe('Sizes', () => {
    it('should default to medium size', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal')
      expect(modal?.classList.contains('modal-md')).toBe(true)
    })

    it('should apply small size', async () => {
      mount(Modal, {
        props: { modelValue: true, size: 'sm' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal')
      expect(modal?.classList.contains('modal-sm')).toBe(true)
    })

    it('should apply large size', async () => {
      mount(Modal, {
        props: { modelValue: true, size: 'lg' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal')
      expect(modal?.classList.contains('modal-lg')).toBe(true)
    })

    it('should apply extra large size', async () => {
      mount(Modal, {
        props: { modelValue: true, size: 'xl' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal')
      expect(modal?.classList.contains('modal-xl')).toBe(true)
    })
  })

  // ==========================================================================
  // TITLE / HEADER
  // ==========================================================================

  describe('Title / Header', () => {
    it('should render title prop', async () => {
      mount(Modal, {
        props: { modelValue: true, title: 'Edit User' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const title = document.querySelector('.modal-title')
      expect(title).toBeTruthy()
      expect(title?.textContent).toBe('Edit User')
    })

    it('should render custom header slot', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: {
          header: '<div class="custom-header">Custom Header</div>',
          default: 'Content'
        },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.custom-header')).toBeTruthy()
      expect(document.querySelector('.custom-header')?.textContent).toBe('Custom Header')
      expect(document.querySelector('.modal-title')).toBeFalsy()
    })

    it('should render close button by default', async () => {
      mount(Modal, {
        props: { modelValue: true, title: 'Modal' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const closeBtn = document.querySelector('.modal-close')
      expect(closeBtn).toBeTruthy()
      // Close button uses Lucide X icon (SVG), not text
      expect(closeBtn?.querySelector('svg')).toBeTruthy()
    })

    it('should hide close button when showClose=false', async () => {
      mount(Modal, {
        props: { modelValue: true, title: 'Modal', showClose: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-close')).toBeFalsy()
    })

    it('should NOT render header when no title and no header slot', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-header')).toBeFalsy()
    })
  })

  // ==========================================================================
  // FOOTER SLOT
  // ==========================================================================

  describe('Footer Slot', () => {
    it('should render footer slot', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: {
          default: 'Content',
          footer: '<button class="save-btn">Save</button>'
        },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-footer')).toBeTruthy()
      expect(document.querySelector('.save-btn')).toBeTruthy()
    })

    it('should NOT render footer when no slot provided', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      expect(document.querySelector('.modal-footer')).toBeFalsy()
    })
  })

  // ==========================================================================
  // CLOSE EVENTS
  // ==========================================================================

  describe('Close Events', () => {
    it('should emit update:modelValue and close on close button click', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true, title: 'Modal' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const closeBtn = document.querySelector('.modal-close') as HTMLElement
      closeBtn?.click()
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('should close on backdrop click by default', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const backdrop = document.querySelector('.modal-backdrop') as HTMLElement
      backdrop?.click()
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    })

    it('should NOT close on backdrop click when closeOnBackdrop=false', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true, closeOnBackdrop: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const backdrop = document.querySelector('.modal-backdrop') as HTMLElement
      backdrop?.click()
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })

    it('should NOT close on modal content click', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal') as HTMLElement
      modal?.click()
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })
  })

  // ==========================================================================
  // ESC KEY
  // ==========================================================================

  describe('ESC Key', () => {
    it('should close on ESC key by default', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const event = new KeyboardEvent('keydown', { key: 'Escape' })
      document.dispatchEvent(event)
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    })

    it('should NOT close on ESC when closeOnEsc=false', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true, closeOnEsc: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const event = new KeyboardEvent('keydown', { key: 'Escape' })
      document.dispatchEvent(event)
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })

    it('should NOT close on ESC when modal is closed', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const event = new KeyboardEvent('keydown', { key: 'Escape' })
      document.dispatchEvent(event)
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })

    it('should NOT close on other keys', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const event = new KeyboardEvent('keydown', { key: 'Enter' })
      document.dispatchEvent(event)
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })
  })

  // ==========================================================================
  // BODY SCROLL LOCK
  // ==========================================================================

  describe('Body Scroll Lock', () => {
    it('should lock body scroll when modal opens', async () => {
      const wrapper = mount(Modal, {
        props: { modelValue: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })

      expect(document.body.style.overflow).toBe('')

      await wrapper.setProps({ modelValue: true })
      await flushPromises()

      expect(document.body.style.overflow).toBe('hidden')
    })

    it('should unlock body scroll when modal closes', async () => {
      // Start with modal closed (clean slate)
      const wrapper = mount(Modal, {
        props: { modelValue: false },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })

      // Open modal
      await wrapper.setProps({ modelValue: true })
      await flushPromises()
      expect(document.body.style.overflow).toBe('hidden')

      // Close modal
      await wrapper.setProps({ modelValue: false })
      await flushPromises()

      expect(document.body.style.overflow).toBe('')
    })

    it('should restore body scroll on unmount', async () => {
      document.body.style.overflow = 'hidden'

      const wrapper = mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      wrapper.unmount()

      expect(document.body.style.overflow).toBe('')
    })
  })

  // ==========================================================================
  // ARIA ATTRIBUTES
  // ==========================================================================

  describe('ARIA Attributes', () => {
    it('should have correct ARIA attributes', async () => {
      mount(Modal, {
        props: { modelValue: true },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const modal = document.querySelector('.modal')
      expect(modal?.getAttribute('role')).toBe('dialog')
      expect(modal?.getAttribute('aria-modal')).toBe('true')
    })

    it('should have aria-label on close button', async () => {
      mount(Modal, {
        props: { modelValue: true, title: 'Modal' },
        slots: { default: 'Content' },
        attachTo: attachTarget
      })
      await flushPromises()

      const closeBtn = document.querySelector('.modal-close')
      expect(closeBtn?.getAttribute('aria-label')).toBe('Close modal')
    })
  })
})
