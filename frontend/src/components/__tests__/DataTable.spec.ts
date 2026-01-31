/**
 * GESTIMA DataTable Component Tests
 *
 * Tests table rendering, sorting, pagination, and selection.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '../ui/DataTable.vue'
import type { Column } from '../ui/DataTable.vue'

describe('DataTable Component', () => {
  const mockData = [
    { id: 1, name: 'Alice', age: 25, active: true },
    { id: 2, name: 'Bob', age: 30, active: false },
    { id: 3, name: 'Charlie', age: 35, active: true }
  ]

  const mockColumns: Column[] = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'age', label: 'Age', sortable: true, format: 'number' },
    { key: 'active', label: 'Active', format: 'boolean' }
  ]

  // ==========================================================================
  // RENDERING
  // ==========================================================================

  describe('Rendering', () => {
    it('should render table with data', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns
        }
      })

      expect(wrapper.find('table').exists()).toBe(true)
      expect(wrapper.findAll('tbody tr')).toHaveLength(3)
    })

    it('should render column headers', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns
        }
      })

      const headers = wrapper.findAll('th')
      expect(headers[0]!.text()).toContain('Name')
      expect(headers[1]!.text()).toContain('Age')
      expect(headers[2]!.text()).toContain('Active')
    })

    it('should render cell values', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns
        }
      })

      const firstRow = wrapper.findAll('tbody tr')[0]!
      const cells = firstRow.findAll('td')

      expect(cells[0]!.text()).toBe('Alice')
      expect(cells[1]!.text()).toContain('25') // formatNumber adds spaces
      expect(cells[2]!.text()).toBe('✓') // boolean format
    })

    it('should show loading state', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns,
          loading: true
        }
      })

      expect(wrapper.find('.data-table-loading').exists()).toBe(true)
      expect(wrapper.find('table').exists()).toBe(false)
    })

    it('should show empty state', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: [],
          columns: mockColumns
        }
      })

      expect(wrapper.find('.data-table-empty').exists()).toBe(true)
      expect(wrapper.text()).toContain('Žádná data k zobrazení')
    })

    it('should show custom empty text', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: [],
          columns: mockColumns,
          emptyText: 'No results found'
        }
      })

      expect(wrapper.text()).toContain('No results found')
    })
  })

  // ==========================================================================
  // COLUMN VISIBILITY
  // ==========================================================================

  describe('Column Visibility', () => {
    it('should hide columns with visible=false', () => {
      const columns: Column[] = [
        { key: 'name', label: 'Name', visible: true },
        { key: 'age', label: 'Age', visible: false },
        { key: 'active', label: 'Active' }
      ]

      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns
        }
      })

      const headers = wrapper.findAll('th')
      expect(headers).toHaveLength(2) // Only name and active
      expect(headers[0]!.text()).toContain('Name')
      expect(headers[1]!.text()).toContain('Active')
    })
  })

  // ==========================================================================
  // FORMATTING
  // ==========================================================================

  describe('Formatting', () => {
    it('should format currency', () => {
      const data = [{ id: 1, price: 1234.56 }]
      const columns: Column[] = [
        { key: 'price', label: 'Price', format: 'currency' }
      ]

      const wrapper = mount(DataTable, {
        props: { data, columns }
      })

      const cell = wrapper.find('tbody td')
      const text = cell.text().replace(/\u00A0/g, ' ') // Replace non-breaking space
      expect(text).toContain('1 234,56')
      expect(text).toContain('Kč')
    })

    it('should format number', () => {
      const data = [{ id: 1, count: 1000 }]
      const columns: Column[] = [
        { key: 'count', label: 'Count', format: 'number' }
      ]

      const wrapper = mount(DataTable, {
        props: { data, columns }
      })

      const cell = wrapper.find('tbody td')
      const text = cell.text().replace(/\u00A0/g, ' ') // Replace non-breaking space
      expect(text).toContain('1 000')
    })

    it('should format boolean', () => {
      const data = [
        { id: 1, active: true },
        { id: 2, active: false }
      ]
      const columns: Column[] = [
        { key: 'active', label: 'Active', format: 'boolean' }
      ]

      const wrapper = mount(DataTable, {
        props: { data, columns }
      })

      const cells = wrapper.findAll('tbody td')
      expect(cells[0]!.text()).toBe('✓')
      expect(cells[1]!.text()).toBe('✗')
    })

    it('should show dash for null/undefined', () => {
      const data = [{ id: 1, value: null }]
      const columns: Column[] = [
        { key: 'value', label: 'Value' }
      ]

      const wrapper = mount(DataTable, {
        props: { data, columns }
      })

      const cell = wrapper.find('tbody td')
      expect(cell.text()).toBe('—')
    })
  })

  // ==========================================================================
  // SORTING
  // ==========================================================================

  describe('Sorting', () => {
    it('should show sort icons on sortable columns', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns
        }
      })

      const nameHeader = wrapper.findAll('th')[0]!
      expect(nameHeader.classes()).toContain('sortable')
      expect(nameHeader.find('.sort-icon').exists()).toBe(true)
    })

    it('should emit sort event on header click', async () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns
        }
      })

      const nameHeader = wrapper.findAll('th')[0]!
      await nameHeader.trigger('click')

      expect(wrapper.emitted('sort')).toBeTruthy()
      expect(wrapper.emitted('sort')![0]).toEqual([
        { key: 'name', direction: 'asc' }
      ])
    })

    it('should toggle sort direction', async () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns,
          sortKey: 'name',
          sortDirection: 'asc'
        }
      })

      const nameHeader = wrapper.findAll('th')[0]!
      await nameHeader.trigger('click')

      expect(wrapper.emitted('sort')![0]).toEqual([
        { key: 'name', direction: 'desc' }
      ])
    })

    it('should show sort direction indicator', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns,
          sortKey: 'name',
          sortDirection: 'asc'
        }
      })

      const nameHeader = wrapper.findAll('th')[0]!
      expect(nameHeader.classes()).toContain('sorted')
      expect(nameHeader.text()).toContain('↑')
    })

    it('should NOT emit sort on non-sortable columns', async () => {
      const columns: Column[] = [
        { key: 'name', label: 'Name', sortable: false }
      ]

      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns
        }
      })

      const nameHeader = wrapper.find('th')
      await nameHeader.trigger('click')

      expect(wrapper.emitted('sort')).toBeFalsy()
    })
  })

  // ==========================================================================
  // ROW CLICK
  // ==========================================================================

  describe('Row Click', () => {
    it('should emit row-click event', async () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns,
          rowClickable: true
        }
      })

      const firstRow = wrapper.find('tbody tr')
      await firstRow.trigger('click')

      expect(wrapper.emitted('row-click')).toBeTruthy()
      expect(wrapper.emitted('row-click')![0]).toEqual([mockData[0], 0])
    })

    it('should add clickable class when rowClickable=true', () => {
      const wrapper = mount(DataTable, {
        props: {
          data: mockData,
          columns: mockColumns,
          rowClickable: true
        }
      })

      const firstRow = wrapper.find('tbody tr')
      expect(firstRow.classes()).toContain('clickable')
    })
  })

  // ==========================================================================
  // PAGINATION
  // ==========================================================================

  describe('Pagination', () => {
    const paginationProps = {
      data: mockData,
      columns: mockColumns,
      pagination: {
        page: 1,
        perPage: 10,
        total: 25
      }
    }

    it('should render pagination controls', () => {
      const wrapper = mount(DataTable, { props: paginationProps })

      expect(wrapper.find('.data-table-pagination').exists()).toBe(true)
      expect(wrapper.text()).toContain('Strana 1 z 3')
      expect(wrapper.text()).toContain('Zobrazeno 1-10 z 25') // perPage=10, shows 1-10
    })

    it('should disable previous button on first page', () => {
      const wrapper = mount(DataTable, { props: paginationProps })

      const prevBtn = wrapper.findAll('.pagination-btn')[0]!
      expect(prevBtn.attributes('disabled')).toBeDefined()
    })

    it('should enable next button when hasNextPage', () => {
      const wrapper = mount(DataTable, { props: paginationProps })

      const nextBtn = wrapper.findAll('.pagination-btn')[1]!
      expect(nextBtn.attributes('disabled')).toBeUndefined()
    })

    it('should disable next button on last page', () => {
      const wrapper = mount(DataTable, {
        props: {
          ...paginationProps,
          pagination: { page: 3, perPage: 10, total: 25 }
        }
      })

      const nextBtn = wrapper.findAll('.pagination-btn')[1]!
      expect(nextBtn.attributes('disabled')).toBeDefined()
    })

    it('should emit page-change on button click', async () => {
      const wrapper = mount(DataTable, { props: paginationProps })

      const nextBtn = wrapper.findAll('.pagination-btn')[1]!
      await nextBtn.trigger('click')

      expect(wrapper.emitted('page-change')).toBeTruthy()
      expect(wrapper.emitted('page-change')![0]).toEqual([2])
    })

    it('should emit per-page-change on select change', async () => {
      const wrapper = mount(DataTable, { props: paginationProps })

      const select = wrapper.find('.pagination-per-page select')
      await select.setValue(25)

      expect(wrapper.emitted('per-page-change')).toBeTruthy()
      expect(wrapper.emitted('per-page-change')![0]).toEqual([25])
    })
  })

  // ==========================================================================
  // NESTED KEYS
  // ==========================================================================

  describe('Nested Keys', () => {
    it('should access nested properties', () => {
      const data = [
        { id: 1, user: { name: 'Alice', email: 'alice@example.com' } }
      ]
      const columns: Column[] = [
        { key: 'user.name', label: 'Name' },
        { key: 'user.email', label: 'Email' }
      ]

      const wrapper = mount(DataTable, {
        props: { data, columns }
      })

      const cells = wrapper.findAll('tbody td')
      expect(cells[0]!.text()).toBe('Alice')
      expect(cells[1]!.text()).toBe('alice@example.com')
    })
  })
})
