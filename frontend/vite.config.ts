import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import fs from "fs"

// Read domain configuration from backend config
function getDomainConfig() {
  try {
    const configPath = path.resolve(__dirname, '../backend/config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    return {
      domain: config.domain?.name || process.env.VITE_DOMAIN || 'tnyr.me',
      apiBaseUrl: config.domain?.api_base_url || process.env.VITE_API_BASE_URL || `https://${config.domain?.name || 'tnyr.me'}`
    };
  } catch (error) {
    console.warn('Could not read backend config, using environment variables or defaults');
    return {
      domain: process.env.VITE_DOMAIN || 'tnyr.me',
      apiBaseUrl: process.env.VITE_API_BASE_URL || `https://${process.env.VITE_DOMAIN || 'tnyr.me'}`
    };
  }
}

// Plugin to replace environment variables in HTML and other static files
function replaceEnvVars() {
  return {
    name: 'replace-env-vars',
    generateBundle(_options: any, bundle: any) {
      const { domain } = getDomainConfig()
      
      Object.keys(bundle).forEach(fileName => {
        const file = bundle[fileName]
        if (file.type === 'asset') {
          if (typeof file.source === 'string') {
            file.source = file.source.replace(/%VITE_DOMAIN%/g, domain)
          } else if (file.source instanceof Uint8Array) {
            const text = new TextDecoder().decode(file.source)
            if (text.includes('%VITE_DOMAIN%')) {
              const replaced = text.replace(/%VITE_DOMAIN%/g, domain)
              file.source = new TextEncoder().encode(replaced)
            }
          }
        }
      })
    }
  }
}
 
const { domain, apiBaseUrl } = getDomainConfig();

export default defineConfig({
  plugins: [react(), replaceEnvVars()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../backend/dist"),
    emptyOutDir: true,
  },
  define: {
    'import.meta.env.VITE_DOMAIN': JSON.stringify(domain),
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiBaseUrl),
  },
})