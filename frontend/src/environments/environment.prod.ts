// Production environment configuration
// Runtime config via window.__env (set by Docker environment variable API_TEST_DELAY)
declare const window: any;

export const environment = {
  production: true,
  version: '1.0.0',
  // API test delay in milliseconds (0 = disabled)
  // Can be overridden at runtime via API_TEST_DELAY Docker env var
  get apiTestDelay(): number {
    return (typeof window !== 'undefined' && window.__env?.apiTestDelay) || 0;
  }
};
