## v0.1.3 (07-06-2024)

### Improvement

- Ensure compatibility with v12 dbt manifest schema that was released as part of dbt-core v1.8.

## v0.1.2 (29-12-2023)

### Improvement

- Ensure compatibility for the `--static` flag in `dbt docs generate`.

### Fixes

- Render diagrams on back-and-forth navigation as well. Before, some diagrams went unrendered.

## v0.1.1 (27-12-2023)

### Fixes

- Make Playwright an extras dependency. It's only required for SVG rendering.
- Ensure compatibility with v11 dbt manifest schema that was released as part of dbt-core v1.7.
- Add `--version` flag to CLI.
