/**
 * Test data generators for E2E tests
 */

/**
 * Generate unique part number for testing
 */
export function generatePartNumber(): string {
  const timestamp = Date.now().toString().slice(-6);
  return `1${timestamp}`;
}

/**
 * Generate test part data
 */
export function generatePartData(overrides?: Partial<{
  name: string;
  description: string;
}>) {
  const timestamp = Date.now();
  return {
    name: overrides?.name || `Test Part ${timestamp}`,
    description: overrides?.description || `E2E test part created at ${new Date().toISOString()}`,
  };
}

/**
 * Generate test batch data
 */
export function generateBatchData(quantity: number) {
  return {
    quantity,
  };
}

/**
 * Default test credentials
 */
/**
 * Generate test partner data
 */
export function generatePartnerData(overrides?: Partial<{
  company_name: string;
  email: string;
}>) {
  const timestamp = Date.now();
  return {
    company_name: overrides?.company_name || `E2E Partner ${timestamp}`,
    email: overrides?.email || `test${timestamp}@example.com`,
  };
}

/**
 * Generate test quote data
 */
export function generateQuoteData(overrides?: Partial<{
  title: string;
  description: string;
}>) {
  const timestamp = Date.now();
  return {
    title: overrides?.title || `E2E Quote ${timestamp}`,
    description: overrides?.description || `E2E test quote created at ${new Date().toISOString()}`,
  };
}

/**
 * Default test credentials
 */
export const TEST_CREDENTIALS = {
  admin: {
    username: 'demo',
    password: 'demo123',
  },
};
