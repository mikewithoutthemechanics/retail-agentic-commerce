# Apps SDK Implementation Review

## Overview
Review of the Apps SDK implementation in `src/apps_sdk/` against the specification in `docs/specs/apps-sdk-spec.md`.

## Findings

### ✅ MCP Server Implementation and Tool Registration
- **Compliant**: Uses FastMCP with proper initialization (`name="acp-merchant"`, `stateless_http=True`)
- Tools registered via `@mcp._mcp_server.list_tools()` decorator
- Each tool includes required fields: `name`, `title`, `description`, `inputSchema`, `outputSchema`, `_meta`, and `annotations`
- Metadata functions (`_search_meta`, `_cart_meta`, etc.) return proper OpenAI-specific fields

### ✅ Widget HTML Resource Serving
- **Compliant**: Resources registered via `@mcp._mcp_server.list_resources()`
- Returns `types.Resource` with correct fields:
  - `uri`: `"ui://widget/merchant-app.html"`
  - `mimeType`: `"text/html+skybridge"`
  - `_meta`: Includes `"openai/widgetAccessible": True`
- Note: Uses single widget approach vs. specification's multiple widget example, but this is acceptable

### ✅ Tool Input/Output Schema Compliance
- **Compliant**: Uses Pydantic models for input/output schemas
- Uses `model_json_schema(by_alias=True)` for schema generation
- Handlers return `types.ServerResult(types.CallToolResult(...))` with `structuredContent`
- Proper error handling with `isError` flag

### ✅ Metadata Compliance
- **Compliant**: Metadata functions return required OpenAI fields:
  - `openai/outputTemplate`: Points to widget URI
  - `openai/toolInvocation/invoking` and `invoked`: Status messages
  - `openai/widgetAccessible`: Set to `true`
  - Cart tools conditionally add `openai/widgetSessionId` when `cart_id` provided
  - Checkout tool conditionally adds `openai/closeWidget: True` when confirmation=True

### ✅ window.openai Bridge Implementation in Widgets
- **Compliant**: Implements all required hooks matching specification:
  - `useOpenAiGlobal` (spec lines 557-609)
  - `useWidgetState` (spec lines 617-662)
  - `useCallTool` (spec lines 668-704)
- Widget correctly uses:
  - `window.openai.callTool()` for MCP communication
  - `window.openai.toolOutput` for data consumption
  - `window.openai.setWidgetState()` for persistence
  - `@openai/apps-sdk-ui/theme` for theme handling

### ✅ State Management with widgetSessionId
- **Compliant**: 
  - Cart-related tools include `openai/widgetSessionId` in metadata when available
  - Widget uses `useWidgetState` hook to persist state across re-renders
  - State synchronized with `window.openai.widgetState` via hook
  - Cart state recovered from ACP session when available

### ✅ UX Principles Compliance
- **Compliant**:
  - Responsive design with Tailwind CSS
  - Follows theme from `window.openai.theme`
  - Implements proper loading states
  - Clear navigation (browse, product detail, checkout)
  - Recommendation tracking via `track-recommendation-click` tool
  - Graceful empty state handling
  - Modal-pattern navigation via state changes

### ⚠️ Deployment Considerations (Partially Compliant)
- **Widget Bundle**: 
  - Uses Vite with React but does NOT configure single-file bundle as recommended in spec
  - `vite.config.ts` lacks:
    ```javascript
    build: {
      rollupOptions: {
        input: { /* widget entries */ },
        // ...
      },
      assetsInlineLimit: 100000, // Inline assets for single-file widgets
    }
    ```
  - Currently produces multi-file build (HTML + JS + CSS chunks)
  - While functional (widget_endpoints.py serves assets correctly), single-file bundle is preferred for iframe efficiency
- **Build Process**: 
  - `package.json` includes `"build": "tsc && vite build"`
  - Missing `vite-plugin-singlefile` configuration despite being in devDependencies

## Recommendations
1. **Configure Vite for single-file widget bundle** using `vite-plugin-singlefile` as shown in specification example
2. **Consider modular widget approach** (separated widgets for different views) though current single-widget implementation is acceptable
3. **Verify build output** contains proper `index.html` that references generated assets

## Compliance Summary
| Area | Status | Notes |
|------|--------|-------|
| MCP Server Implementation | ✅ Compliant | Follows spec exactly |
| Widget Resource Serving | ✅ Compliant | Single widget approach acceptable |
| Tool Schemas | ✅ Compliant | Proper Pydantic usage |
| Metadata Compliance | ✅ Compliant | All required fields present |
| window.openai Bridge | ✅ Compliant | All hooks implemented correctly |
| State Management | ✅ Compliant | widgetSessionId used properly |
| UX Principles | ✅ Compliant | Follows spec guidelines |
| Deployment | ⚠️ Partial | Missing single-file bundle optimization |

## Files Examined
- `src/apps_sdk/main.py` - MCP server implementation
- `src/apps_sdk/widget_endpoints.py` - Widget serving endpoints
- `src/apps_sdk/web/src/hooks/*.ts` - React hooks implementation
- `src/apps_sdk/web/src/App.tsx` - Main widget component
- `src/apps_sdk/web/vite.config.ts` - Build configuration
- `src/apps_sdk/web/package.json` - Dependencies and scripts