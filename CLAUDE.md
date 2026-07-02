# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is the home for Posit Connect extensions - apps, dashboards, and reports that can be installed on Posit Connect servers via the Connect Gallery. Extensions are bundled as TAR files and released via GitHub Releases.

## Key Commands

```bash
# Create a new extension directory structure
make create-extension DIR="my-extension-name"

# Generate manifest.json for Python content
rsconnect-python write-manifest <app-type> .

# Generate manifest.json for R content
rsconnect::writeManifest()

# Update extension list after releases (run from scripts/)
npm ci && npm run update-extension-list
```

## Creating an Extension

1. Run `make create-extension DIR="extension-name"` to create the directory
2. Add your app files (app.py, requirements.txt, etc.)
3. Generate manifest.json using rsconnect or rsconnect-python
4. Manually add the `extension` section to manifest.json (see below)
5. Add a README.md documenting setup and usage
6. Register in `.github/workflows/extensions.yml`

### Required manifest.json Extension Section

```json
{
  "extension": {
    "name": "extension-name",
    "title": "Human Readable Title",
    "description": "Description for the gallery",
    "homepage": "https://github.com/posit-dev/connect-extensions/tree/main/extensions/extension-name",
    "category": "extension|example",
    "tags": ["python", "shiny", "quarto", "r", "fastapi", "mcp", "llm", "chat"],
    "minimumConnectVersion": "2025.04.0",
    "requiredFeatures": ["API Publishing", "OAuth Integrations", "Current User Execution"],
    "version": "0.0.0"
  },
  "environment": {
    "python": { "requires": "~=3.8" },
    "r": { "requires": "~=4.2" }
  }
}
```

- Use `version: "0.0.0"` during development (never releases)
- Valid categories/tags/requiredFeatures are defined in `extensions.json`
- The `~=` operator means "compatible release" (e.g., `~=4.2` means >=4.2, <5.0)

## CI/CD Architecture

### Simple Extensions
Extensions that can be directly TAR'd without build steps:
1. Add filter to `simple-extension-changes` job in `.github/workflows/extensions.yml`
2. On PR: lint, package, run Connect integration tests
3. On merge to main: release if version incremented

### Complex Extensions
Extensions requiring build steps (e.g., TypeScript compilation):
1. Create custom workflow in `.github/workflows/` using template from `docs/creating-a-custom-workflow.md`
2. Add to `complex-extension-changes` job outputs
3. Call custom workflow from `extensions.yml`

### Release Process
- Versions are compared against GitHub Releases
- Incrementing `extension.version` and merging to main triggers release
- `extensions.json` is auto-updated after releases by CI

## Key Files

- `extensions.json` - Registry of all released extensions, valid categories/tags/features
- `.github/actions/lint-extension/` - Validates manifest.json structure
- `.github/actions/package-extension/` - Creates TAR bundle
- `.github/actions/release-extension/` - Creates GitHub Release
- `scripts/extension-list.ts` - Updates extensions.json after releases

## R Package Repository

For R extensions, use Posit Public Package Manager in `~/.Rprofile`:
```r
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
```
