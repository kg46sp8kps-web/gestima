/**
 * GESTIMA - Files Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFilesStore } from '../files'
import { filesApi } from '@/api/files'
import type { FileListResponse, FileWithLinks } from '@/types/file'

// Mock filesApi
vi.mock('@/api/files', () => ({
  filesApi: {
    list: vi.fn(),
    get: vi.fn(),
    upload: vi.fn(),
    delete: vi.fn(),
    link: vi.fn(),
    unlink: vi.fn(),
    setPrimary: vi.fn(),
    getOrphans: vi.fn(),
    getDownloadUrl: vi.fn()
  }
}))

// Mock UI store
vi.mock('../ui', () => ({
  useUiStore: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn()
  })
}))

describe('Files Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with empty state', () => {
    const store = useFilesStore()

    expect(store.files).toEqual([])
    expect(store.selectedFile).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.total).toBe(0)
  })

  it('fetches files from API', async () => {
    const store = useFilesStore()
    const mockResponse: FileListResponse = {
      files: [
        {
          id: 1,
          file_hash: 'a'.repeat(64),
          file_path: 'parts/10900635/rev_A.pdf',
          original_filename: 'test.pdf',
          file_size: 1024,
          file_type: 'pdf',
          mime_type: 'application/pdf',
          status: 'active' as const,
          created_at: '2026-02-15T10:00:00Z',
          updated_at: '2026-02-15T10:00:00Z',
          created_by: 'admin',
          updated_by: null,
          links: []
        }
      ],
      total: 1
    }

    vi.mocked(filesApi.list).mockResolvedValue(mockResponse)

    await store.fetchFiles()

    expect(store.files).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('selects a file by ID', async () => {
    const store = useFilesStore()
    const mockFile: FileWithLinks = {
      id: 1,
      file_hash: 'a'.repeat(64),
      file_path: 'parts/10900635/rev_A.pdf',
      original_filename: 'test.pdf',
      file_size: 1024,
      file_type: 'pdf',
      mime_type: 'application/pdf',
      status: 'active' as const,
      created_at: '2026-02-15T10:00:00Z',
      updated_at: '2026-02-15T10:00:00Z',
      created_by: 'admin',
      updated_by: null,
      links: []
    }

    vi.mocked(filesApi.get).mockResolvedValue(mockFile)

    await store.selectFile(1)

    expect(store.selectedFile).toEqual(mockFile)
    expect(store.loading).toBe(false)
  })

  it('uploads a file', async () => {
    const store = useFilesStore()
    const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const mockUploadResponse = {
      id: 1,
      file_hash: 'a'.repeat(64),
      file_path: 'loose/test.pdf',
      original_filename: 'test.pdf',
      file_size: 4,
      file_type: 'pdf',
      mime_type: 'application/pdf',
      status: 'active' as const,
      created_at: '2026-02-15T10:00:00Z',
      updated_at: '2026-02-15T10:00:00Z',
      created_by: 'admin',
      updated_by: null,
      link: null
    }

    vi.mocked(filesApi.upload).mockResolvedValue(mockUploadResponse)

    await store.uploadFile(mockFile, { directory: 'loose' })

    expect(store.files).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(filesApi.upload).toHaveBeenCalledWith(mockFile, { directory: 'loose' })
  })

  it('deletes a file', async () => {
    const store = useFilesStore()
    store.files = [
      {
        id: 1,
        file_hash: 'a'.repeat(64),
        file_path: 'parts/10900635/rev_A.pdf',
        original_filename: 'test.pdf',
        file_size: 1024,
        file_type: 'pdf',
        mime_type: 'application/pdf',
        status: 'active' as const,
        created_at: '2026-02-15T10:00:00Z',
        updated_at: '2026-02-15T10:00:00Z',
        created_by: 'admin',
        updated_by: null,
        links: []
      }
    ]
    store.total = 1

    vi.mocked(filesApi.delete).mockResolvedValue()

    await store.deleteFile(1)

    expect(store.files).toHaveLength(0)
    expect(store.total).toBe(0)
  })

  it('computes orphan files correctly', () => {
    const store = useFilesStore()
    store.files = [
      {
        id: 1,
        file_hash: 'a'.repeat(64),
        file_path: 'parts/10900635/rev_A.pdf',
        original_filename: 'orphan.pdf',
        file_size: 1024,
        file_type: 'pdf',
        mime_type: 'application/pdf',
        status: 'active' as const,
        created_at: '2026-02-15T10:00:00Z',
        updated_at: '2026-02-15T10:00:00Z',
        created_by: 'admin',
        updated_by: null,
        links: []
      },
      {
        id: 2,
        file_hash: 'b'.repeat(64),
        file_path: 'parts/10900635/rev_B.pdf',
        original_filename: 'linked.pdf',
        file_size: 2048,
        file_type: 'pdf',
        mime_type: 'application/pdf',
        status: 'active' as const,
        created_at: '2026-02-15T10:00:00Z',
        updated_at: '2026-02-15T10:00:00Z',
        created_by: 'admin',
        updated_by: null,
        links: [
          {
            id: 1,
            file_id: 2,
            entity_type: 'part',
            entity_id: 123,
            entity_name: null,
            is_primary: true,
            revision: 'A',
            link_type: 'drawing',
            created_at: '2026-02-15T10:00:00Z',
            created_by: 'admin'
          }
        ]
      }
    ]

    expect(store.orphanFiles).toHaveLength(1)
    expect(store.orphanFiles[0]?.original_filename).toBe('orphan.pdf')
  })
})
