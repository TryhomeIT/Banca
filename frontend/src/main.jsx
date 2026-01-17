import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ConvexProvider, ConvexReactClient } from "convex/react";
import './index.css'
import App from './App.jsx'

// Runtime configuration support
const runtimeUrl = window.ENV && window.ENV.CONVEX_URL;
const buildTimeUrl = import.meta.env.VITE_CONVEX_URL;
const convexUrl = runtimeUrl || buildTimeUrl;

console.log("🔍 Debug: Runtime URL:", runtimeUrl);
console.log("🔍 Debug: Build-time URL:", buildTimeUrl);
console.log("🔍 Debug: Final Convex URL:", convexUrl);

if (!convexUrl || convexUrl === "") {
  console.error("❌ Convex URL is missing! Check window.ENV.CONVEX_URL or VITE_CONVEX_URL.");
}

const convex = new ConvexReactClient(convexUrl || "https://placeholder.convex.cloud");

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ConvexProvider client={convex}>
      <App />
    </ConvexProvider>
  </StrictMode>,
)
