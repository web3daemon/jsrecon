// Build-time config. Values come from .env through the bundler's define step.

export const API_BASE = "https://api.example.com/v2";
export const CDN_BASE = "https://cdn.example.com";
export const REQUEST_TIMEOUT_MS = 30_000;

// Upload keys for the product-photo bucket. This belongs on the server —
// it's here on purpose, so `jsrecon map` has something to catch in the demo.
// AKIAIOSFODNN7EXAMPLE is AWS's own documentation placeholder, not a real key.
export const S3_UPLOAD_KEY = "AKIAIOSFODNN7EXAMPLE";
