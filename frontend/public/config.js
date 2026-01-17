// Runtime configuration
// This file is overwritten by Docker at startup
window.ENV = {
  CONVEX_URL: "" // Will fall back to import.meta.env in dev
};
