# Creating a custom workflow

Most custom workflows will have common steps. They utilize handy
[composite GitHub Actions](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action)
in the repository.

A good place to start is looking at examples of custom workflows already in the
repository like the [Publisher Command Center workflow](https://github.com/posit-dev/connect-extensions/blob/main/.github/workflows/publisher-command-center.yml).

## Custom Workflow Template

Use the template below to get started. It contains inline comments to explain
each section.

Replace the `EXTENSION_NAME` variable with your content's name, and add the
custom build steps needed for your content. The custom steps will entirely
depend on your content and what environment it needs to setup.

```yaml
# ./github/workflows/my-custom-content.yml

name: My Custom Content

# Re-usable workflows use the `workflow_call` trigger
# https://docs.github.com/en/actions/sharing-automations/reusing-workflows#creating-a-reusable-workflow
on:
  workflow_call:

# Setup the environment with the extension name for easy re-use
# Also set the GH_TOKEN for the release-extension action to be able to use gh
env:
  EXTENSION_NAME: my-content-name
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

jobs:
  extension:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./extensions/${{ env.EXTENSION_NAME }}

    steps:
      # Checkout the repository so the rest of the actions can run with no issue
      - uses: actions/checkout@v4

      # We want to fail quickly if the linting fails, do that first
      - uses: ./.github/actions/lint-extension
        with:
          extension-name: ${{ env.EXTENSION_NAME }}

      # ---
      # Add Custom Build Steps Here
      # ---

      # Now that the extension is built we need to upload an artifact to pass
      # to the package-extension action that contains the files we want to be
      # included in the extension
      # This only includes necessary files for the extension to run leaving out
      # the files that were used to build the /dist/ directory
      - name: Upload built extension
        uses: actions/upload-artifact@v4
        with:
          name: ${{ env.EXTENSION_NAME }}
          # Replace the below with the files your content needs
          path: |
            extensions/${{ env.EXTENSION_NAME }}/dist/
            extensions/${{ env.EXTENSION_NAME }}/requirements.txt
            extensions/${{ env.EXTENSION_NAME }}/app.py
            extensions/${{ env.EXTENSION_NAME }}/manifest.json

      # Package up the extension into a TAR using the package-extension action
      - uses: ./.github/actions/package-extension
        with:
          extension-name: ${{ env.EXTENSION_NAME }}
          artifact-name: ${{ env.EXTENSION_NAME }}

  connect-integration-tests:
    needs: extension
    uses: ./.github/workflows/connect-integration-tests.yml
    secrets: inherit
    with:
      extensions: '["publisher-command-center"]'  # JSON array format to match the workflow input schema

  release:
    runs-on: ubuntu-latest
    needs: [extension, connect-integration-tests]
    # Release the extension using the release-extension action
    # Will only create a GitHub release if merged to `main` and the semver
    # version has been updated
    steps:
      # Checkout the repository so the rest of the actions can run with no issue
      - uses: actions/checkout@v4

      - uses: ./.github/actions/release-extension
        with:
          extension-name: ${{ env.EXTENSION_NAME }}
```
