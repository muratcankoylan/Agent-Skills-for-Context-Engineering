# Figma MCP Workflow and Best Practices

This document outlines the best practices for interacting with the Figma MCP (`~~design`).

## 1. Authentication

-   Ensure the user has authenticated the Figma MCP connection. The skill should check for a valid connection before attempting any operations. If no connection is found, gracefully fall back to Standalone mode or inform the user.

## 2. Creating Prototypes (Create Mode)

-   **Source of Truth**: The `DESIGN-BRIEF.md` is the definitive source for prototype creation.
-   **Structure**:
    1.  Create a new Page in the Figma file named after the project.
    2.  For each item in the "Screen Inventory," create a new Frame.
    3.  Populate each Frame with basic placeholder shapes (rectangles for buttons, text blocks) corresponding to the "Elements" listed in the brief.
    4.  Do not attempt to create complex components or perfect visual styles. The goal is to lay out the structure, not to complete the design.

## 3. Inspecting Designs (Inspect Mode)

-   **Targeting**: Prompt the user for the specific Frame or Component URL to inspect.
-   **Data Extraction**: Use the MCP's "get node properties" endpoint to extract:
    -   Fill colors (for color palettes).
    -   Font family, weight, and size (for typography styles).
    -   Layout properties (width, height, padding, margin).
-   **Output**: Format the extracted data into a clean Markdown table of design tokens.

## 4. Exporting Assets (Export Mode)

-   **Format**: Ask the user for the desired export format (e.g., PNG, JPG, SVG).
-   **Scale**: Default to exporting at 2x scale for high-resolution assets.
-   **API Call**: Use the MCP's "export node" endpoint, providing the node ID, format, and scale.
-   **Output**: Present the exported asset directly to the user or save it to the project's directory.
