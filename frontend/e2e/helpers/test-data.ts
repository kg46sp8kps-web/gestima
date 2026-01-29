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
export const TEST_CREDENTIALS = {
  admin: {
    username: 'admin',
    password: 'admin123',
  },
  operator: {
    username: 'operator',
    password: 'operator123',
  },
  viewer: {
    username: 'viewer',
    password: 'viewer123',
  },
};
