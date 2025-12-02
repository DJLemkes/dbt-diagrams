## v0.2.0 (03-12-2025)

### Additions
- `dbt-diagrams docs serve` for local ERD testing.

### Improvement
- Python 3.9–3.12 support.
- Migration to Pydantic 2, Poetry 2, and updated CI/GitHub Pages setup.

### Fixes
- Correct Mermaid rendering for decimal datatypes.

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
