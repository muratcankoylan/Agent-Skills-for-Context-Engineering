# Figma MCP Commands Reference

Cheat sheet for technical commands when using the Figma MCP server.

## 1. Inspecting Files

- `get_file`: Retrieve the full document JSON.
- `get_file_nodes`: Get specific nodes (frames/components) by ID.

## 2. Extraction

- `get_image`: Render a specific node as a PNG/SVG for `prototype-to-video` storyboarding.
- `get_component`: Get metadata for a specific UI component.

## 3. Workflow Examples

- **Token Sync**: "Extract all colors from the 'Colors' frame in file [ID] and save to `brand-assets.json`."
- **Screenshot Capture**: "Generate a PNG of the 'Dashboard' frame and save to `data/1-Projets/ProjectA/screenshots/`."
