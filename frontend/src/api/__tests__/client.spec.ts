/**
 * GESTIMA API Client Tests
 *
 * Tests axios interceptors, error handling, and custom error classes.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import {
  apiClient,
  ApiErrorClass,
  OptimisticLockErrorClass,
  ValidationErrorClass
} from '../client'

describe('API Client', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    mock.restore()
    vi.restoreAllMocks()
  })

  // ==========================================================================
  // CONFIGURATION
  // ==========================================================================

  describe('Configuration', () => {
    it('should have correct base config', () => {
      expect(apiClient.defaults.baseURL).toBe('/api')
      expect(apiClient.defaults.withCredentials).toBe(true)
      expect(apiClient.defaults.timeout).toBe(30000)
      expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
      expect(apiClient.defaults.headers['Accept']).toBe('application/json')
    })
  })

  // ==========================================================================
  // SUCCESSFUL REQUESTS
  // ==========================================================================

  describe('Successful Requests', () => {
    it('should make GET request successfully', async () => {
      const responseData = { id: 1, name: 'Test' }
      mock.onGet('/test').reply(200, responseData)

      const response = await apiClient.get('/test')

      expect(response.status).toBe(200)
      expect(response.data).toEqual(responseData)
    })

    it('should make POST request successfully', async () => {
      const postData = { name: 'New Item' }
      const responseData = { id: 1, ...postData }
      mock.onPost('/test', postData).reply(201, responseData)

      const response = await apiClient.post('/test', postData)

      expect(response.status).toBe(201)
      expect(response.data).toEqual(responseData)
    })

    it('should make PUT request successfully', async () => {
      const putData = { name: 'Updated' }
      mock.onPut('/test/1', putData).reply(200, { id: 1, ...putData })

      const response = await apiClient.put('/test/1', putData)

      expect(response.status).toBe(200)
    })

    it('should make DELETE request successfully', async () => {
      mock.onDelete('/test/1').reply(204)

      const response = await apiClient.delete('/test/1')

      expect(response.status).toBe(204)
    })
  })

  // ==========================================================================
  // ERROR HANDLING - Network Errors
  // ==========================================================================

  describe('Network Errors', () => {
    it('should handle network error', async () => {
      mock.onGet('/test').networkError()

      await expect(apiClient.get('/test')).rejects.toThrow(ApiErrorClass)
      await expect(apiClient.get('/test')).rejects.toThrow('Chyba připojení k serveru')
    })

    it('should handle timeout', async () => {
      mock.onGet('/test').timeout()

      await expect(apiClient.get('/test')).rejects.toThrow()
    })
  })

  // ==========================================================================
  // ERROR HANDLING - HTTP Status Codes
  // ==========================================================================

  describe('HTTP Status Codes', () => {
    it('should handle 401 Unauthorized', async () => {
      mock.onGet('/test').reply(401, { detail: 'Unauthorized' })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiErrorClass)
      await expect(apiClient.get('/test')).rejects.toMatchObject({
        status: 401,
        message: 'Unauthorized'
      })

      expect(console.warn).toHaveBeenCalledWith(
        '[API] Unauthorized - redirecting to login'
      )
    })

    it('should handle 403 Forbidden', async () => {
      mock.onGet('/test').reply(403, { detail: 'Forbidden' })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiErrorClass)
      expect(console.warn).toHaveBeenCalledWith(
        '[API] Forbidden - insufficient permissions'
      )
    })

    it('should handle 404 Not Found', async () => {
      mock.onGet('/test').reply(404, { detail: 'Not found' })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiErrorClass)
      await expect(apiClient.get('/test')).rejects.toMatchObject({
        status: 404,
        message: 'Not found'
      })
    })

    it('should handle 409 Conflict (Optimistic Lock)', async () => {
      mock.onPut('/test/1').reply(409, {
        detail: 'Version mismatch',
        expected_version: 2,
        actual_version: 3
      })

      await expect(apiClient.put('/test/1', {})).rejects.toThrow(
        OptimisticLockErrorClass
      )
      await expect(apiClient.put('/test/1', {})).rejects.toMatchObject({
        status: 409,
        message: 'Data byla změněna jiným uživatelem'
      })
    })

    it('should handle 422 Validation Error', async () => {
      mock.onPost('/test').reply(422, {
        detail: [
          { loc: ['body', 'name'], msg: 'Field required' }
        ]
      })

      await expect(apiClient.post('/test', {})).rejects.toThrow(
        ValidationErrorClass
      )
      await expect(apiClient.post('/test', {})).rejects.toMatchObject({
        status: 422,
        message: 'Validation failed'
      })
    })

    it('should handle 500 Internal Server Error', async () => {
      mock.onGet('/test').reply(500, { detail: 'Server error' })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiErrorClass)
      await expect(apiClient.get('/test')).rejects.toMatchObject({
        status: 500,
        message: 'Server error'
      })

      expect(console.error).toHaveBeenCalledWith('[API] Server error')
    })
  })

  // ==========================================================================
  // ERROR DATA PRESERVATION
  // ==========================================================================

  describe('Error Data Preservation', () => {
    it('should preserve error data in ApiError', async () => {
      const errorData = { detail: 'Custom error', code: 'ERR_001' }
      mock.onGet('/test').reply(400, errorData)

      try {
        await apiClient.get('/test')
        expect.fail('Should have thrown error')
      } catch (error: any) {
        expect(error).toBeInstanceOf(ApiErrorClass)
        expect(error.data).toEqual(errorData)
        expect(error.status).toBe(400)
      }
    })

    it('should preserve validation details', async () => {
      const validationData = {
        detail: [
          { loc: ['body', 'name'], msg: 'String should have at least 1 character' },
          { loc: ['body', 'quantity'], msg: 'Input should be greater than 0' }
        ]
      }
      mock.onPost('/test').reply(422, validationData)

      try {
        await apiClient.post('/test', {})
        expect.fail('Should have thrown error')
      } catch (error: any) {
        expect(error).toBeInstanceOf(ValidationErrorClass)
        expect(error.data).toEqual(validationData)
        expect(error.data.detail).toHaveLength(2)
      }
    })
  })

  // ==========================================================================
  // CUSTOM ERROR CLASSES
  // ==========================================================================

  describe('Custom Error Classes', () => {
    it('should create ApiErrorClass correctly', () => {
      const error = new ApiErrorClass('Test error', 400, { foo: 'bar' })

      expect(error).toBeInstanceOf(Error)
      expect(error).toBeInstanceOf(ApiErrorClass)
      expect(error.message).toBe('Test error')
      expect(error.status).toBe(400)
      expect(error.data).toEqual({ foo: 'bar' })
      expect(error.name).toBe('ApiError')
    })

    it('should create OptimisticLockErrorClass correctly', () => {
      const data = { expected_version: 1, actual_version: 2 }
      const error = new OptimisticLockErrorClass(data)

      expect(error).toBeInstanceOf(ApiErrorClass)
      expect(error).toBeInstanceOf(OptimisticLockErrorClass)
      expect(error.message).toBe('Data byla změněna jiným uživatelem')
      expect(error.status).toBe(409)
      expect(error.data).toEqual(data)
      expect(error.name).toBe('OptimisticLockError')
    })

    it('should create ValidationErrorClass correctly', () => {
      const data = { detail: [{ loc: ['name'], msg: 'Invalid' }] }
      const error = new ValidationErrorClass(data)

      expect(error).toBeInstanceOf(ApiErrorClass)
      expect(error).toBeInstanceOf(ValidationErrorClass)
      expect(error.message).toBe('Validation failed')
      expect(error.status).toBe(422)
      expect(error.data).toEqual(data)
      expect(error.name).toBe('ValidationError')
    })
  })

  // ==========================================================================
  // FALLBACK ERROR MESSAGE
  // ==========================================================================

  describe('Fallback Error Message', () => {
    it('should use "Unknown error" when no detail provided', async () => {
      mock.onGet('/test').reply(400, {}) // No "detail" field

      await expect(apiClient.get('/test')).rejects.toMatchObject({
        message: 'Unknown error'
      })
    })

    it('should extract detail from response', async () => {
      mock.onGet('/test').reply(400, { detail: 'Custom error message' })

      await expect(apiClient.get('/test')).rejects.toMatchObject({
        message: 'Custom error message'
      })
    })
  })
})
