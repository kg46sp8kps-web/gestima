/**
 * Quotes Test API - Mock endpoints for development
 *
 * Use these instead of real AI API for faster testing
 */

import { apiClient } from './client'
import type { QuoteRequestReview } from '@/types/quote'

/**
 * Get mock parsed quote request (GELSO AG P20971 fixture)
 *
 * Use this instead of parseQuoteRequest() to test without AI API calls.
 * Returns same structure as real endpoint.
 */
export async function getMockParsedQuoteRequest(): Promise<QuoteRequestReview> {
  const response = await apiClient.get<QuoteRequestReview>('/quotes-test/parse-request-mock')
  return response.data
}

/**
 * Get raw extraction data from fixture
 */
export async function getFixtureExtraction(): Promise<any> {
  const response = await apiClient.get('/quotes-test/fixture/extraction')
  return response.data
}

/**
 * Get review data from fixture
 */
export async function getFixtureReview(): Promise<QuoteRequestReview> {
  const response = await apiClient.get<QuoteRequestReview>('/quotes-test/fixture/review')
  return response.data
}

/**
 * Get quote creation payload from fixture
 */
export async function getFixtureQuoteCreate(): Promise<any> {
  const response = await apiClient.get('/quotes-test/fixture/quote-create')
  return response.data
}
