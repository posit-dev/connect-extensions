# Contributing

Add your extension in the `extensions/` subdirectory.

To help you get started, call `make create-extension DIR=my_extension_name` to
create a new extension directory. Note, you will need to manually create your
`manifest.json` file.

## `manifest.json`

Use `rsconnect` or `rsconnect-python` to generate a manifest, which is required
as part of the extension bundle.

## Use the Posit Public Package Manager as your R package repository

Before you work with R content, set the Posit Public Package Manager as your R
package repository. Put the following in your `~/.Rprofile`:

```r
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
```

It's best to do this this *before* you install packages, run `renv::init()` or
`renv::restore()`, or generate a `manifest.json`. Doing this allows content to
use binary packages when it installs on a Connect server.

See https://packagemanager.posit.co/client/#/repos/cran/setup for more detail.

## Connect Gallery

The Connect Gallery displays apps, dashboards, and reports that can be easily
added to Posit Connect servers.

This section covers how to ready your content for the gallery, add it, and
release new updates.

## Additional Requirements

### The `extension` section in `manifest.json`

Content in the gallery requires some additional details in the `manifest.json`
file to display, install on Connect, and automatically release using automation
in this repository.

Below is an example of the additional details that need to be manually added
to the `manifest.json`:

```json
// manifest.json

{
  ...
  "extension": {
    "name": "my-content-name",
    "title": "My Content Name",
    "description": "A lovely, detailed description of the content.",
    "homepage": "https://github.com/posit-dev/connect-extensions/tree/main/extensions/my-content-name",
    "category": "",
    "tags": [],
    "minimumConnectVersion": "2025.04.0",
    "version": "0.0.0"
  }
}
```

It is recommended to begin with `"version": "0.0.0"` to avoid triggering a
release during development of your content. When you are ready to release to
the gallery check the [Adding content to the Connect Gallery](#adding-content-to-the-connect-gallery) section.

#### Category

The `category` field in the `extension` section of the `manifest.json` is
required to group content in the Gallery.

```json
// manifest.json

{
  ...
  "extension": {
    "category": "extension,
    ...
  }
}
```

Available categories are listed in the [`extensions.json`](./extensions.json)
file. The category should match the `id`, and automations in the repository
will check that the category is valid.

The order of the categories in [`extensions.json`](./extensions.json) determines
the order in which they are displayed in the Connect Gallery.

#### Tags

The `tags` array in the `extension` section of the `manifest.json` is optional,
but it helps users filter content in the Gallery. A good start is to include the
languages and tools used:

```json
// manifest.json

{
  ...
  "extension": {
    "tags": ["python", "quarto"],
    ...
  }
}
```

Available tags are listed in the [`extensions.json`](./extensions.json) and the
automations in the repository will check that any included tags are valid.

##### Adding a new tag to the gallery

If you want to include a tag on content that is not already in the
[`extensions.json`](./extensions.json) file, it can be added.

Pull requests can add new tags, but ensure that the tag follows the patterns
of other tags and is not a duplicate. New tags should be added sparingly and
reviewed carefully.

#### Minimum Connect Version

The `minimumConnectVersion` field in the `extension` section of the
`manifest.json` is required to specify the minimum version of Posit Connect
that the content can be installed and used on.

Each time you release a version of your content the `minimumConnectVersion`
is recorded for that specific release.

A good Connect Version to start with is `"2025.04.0"` since it is the
release that introduced the Connect Gallery.

#### Required Connect Features

The `requiredFeatures` field in the `extension` section of the `manifest.json`
is optional, but if your content requires enhanced features of Posit Connect to
function correctly it should be included.

For example, if your content requires the API Publishing feature your
`manifest.json` should include the following:

```json
// manifest.json

{
  ...
  "extension": {
    "requiredFeatures": ["API Publishing"],
    ...
  }
}
```

### README.md

In the above extension section there is a `homepage` link that we provide in the
Connect Gallery letting users see documentation related to the apps, dashboards,
and reports available to install.

Gallery content should include a `README.md` file in its directory so when the
homepage is visited there is documentation to assist users. It should include
a description of how the content can be used and any additional setup
instructions.

### Language version constraints

To ensure that content in the gallery is installable on as many Posit Connect
servers as possible we use the language version constraints feature to broaden
the language versions Connect can use for a piece of content.

All content in the gallery should include `requires` specifications for the
language(s) it utilizes.

Here is an example of what needs to be included in a `manifest.json`:

```json
// manifest.json

{
  ...
  "environment": {
    "python": {
      "requires": "~=3.8"
    },
    "r": {
      "requires": "~=4.2"
    }
  }
}
```

It is recommended to use the `~=` operator to specify the version of the
language(s) that the content requires for concise display in the Connect Gallery
UI.

`~=` is the "Compatible release" operator. `~=4.2` means "any version greater
than or equal to 4.2 but less than 5.0".

## Adding content to the Connect Gallery

Once your content has the requirements above it is ready to be added to the
Connect Gallery.

The Connect Gallery uses GitHub Workflows to automate releases of new content
when pull requests in this repo merge into `main`.

To add content to the Connect Gallery, follow the steps below:

### Adding simple content

"Simple content" refers to content that can be bundled into a TAR file without
any additional steps. Most content will fall into this category.

> [!NOTE]
> If you can run
> ```bash
> tar -czf my-extension-name.tar.gz ./extensions/my-extension-name
> ```
> and the resulting TAR file can be published by uploading the bundle to Posit
> Connect, then it is piece of simple content.

To add simple content look for the [`simple-extension-changes` section in the `.github/workflows/extensions.yml`](https://github.com/posit-dev/connect-extensions/blob/main/.github/workflows/extensions.yml#L31)
file and add a new filter:

```yml
filters: |
  ...
  my-content-name: extensions/my-content-name/**
```

A good example is how `reaper` is setup.

This will make any code changes to your content trigger a few things:

- lint: ensuring your content has everything it needs to be added to the
  gallery
- package: creating a TAR file of the content's directory to test in pull
  requests and to be released
- test: checking that the content will publish to Connect
- release: When the `version` in the `manifest.json` is increased and merged to
  `main`, releases the content to users of Posit Connect

Lastly set the `version` in the `manifest.json` file to your initial release.

When the changes above are merged the first release will be kicked off, and
your content will be in the gallery. 🚀

### Adding custom built content

"Custom built content" refers to content that requires additional steps prior to
be being packaged into a TAR file.

Setting up custom built content is a bit more complex since it involves
setting up the environment needed to build the content.

#### Creating a custom workflow

To facilitate control over how the content is being built we utilize custom
GitHub Workflows. See the [Creating a custom workflow](docs/creating-a-custom-workflow.md)
guide how to get started.

#### Calling the custom workflow

Once the custom workflow is created we need to head back to the general
[.github/workflows/extensions.yml](https://github.com/posit-dev/connect-extensions/blob/main/.github/workflows/extensions.yml)
file.

It is recommended to see how `publisher-command-center` is setup as an example
for how to use your new custom workflow.

Once your custom workflow is setup, set the `version` in the `manifest.json`
file to your initial release.

When the changes above are merged the first release will be kicked off, and
your content will be in the gallery. 🚀

## Updating content in the Connect Gallery

To update already released content in the Connect Gallery simply increment the
`version` field in the `extension` section of the `manifest.json` file and open
a pull request with the changes.

```json
// manifest.json

{
  ...
  "extension": {
    ...
    "version": "1.1.0"
  }
}
```

If the new version of content requires a new minimum Connect version, then
update the `minimumConnectVersion` as well.

When that pull request is merged, GitHub Workflows will automatically create a
new GitHub Release for the content changed, update the content list, and update
Connect Gallery.

### Checking if your extension will release

If you would like to check if merging a pull request will trigger a new release
you can do that by looking in the GitHub Actions summary. Click on the "Checks"
tab for a Pull Request and then click on the Extension Workflow run and the
summary will be displayed below the workflow graph.

It will say one of the following based on the `version` in the
`manifest.json` and the last released version:

> The manifest version is '1.1.0' and the released version is '1.0.0'
> 🚀 Will release! The manifest version is greater than the released version.

> The manifest version is '1.0.0' and the released version is '1.0.0'
> 😴 Holding back from release: The manifest version is not greater than the released version.

> ⚠️ Version 0.0.0 is reserved and will never be released.

## Manually testing content

Packaged TAR files are included as artifacts in the Extension Workflow runs.

Click on the "Checks" tab for a Pull Request and look at the Extension Workflow
run. At the bottom, "Artifacts" are available, and if your content changed
in the Pull Request then a `my-extension-name.tar.gz` file will be available.

It can be downloaded, and tested using the publish via bundle feature in Posit
Connect.

## Removing a release from the Connect Gallery

If released content needs to be reverted, or content removed entirely, follow
the steps below:

### Removing a single release

Open a pull request to remove the release:

1. Remove the release from the content list in `extension.json`
    - If the removed release is the latest release, update the `latestVersion`
      field for that piece of content to the previous release
    - Versions are sorted in descending order, so the latest release should be
      the first element in the `versions` array
2. Revert the content's `version` in the `manifest.json` file to the previous
   release

Once the pull request is merged continue with the steps below:

1. Remove the associated release from the [GitHub Releases page](https://github.com/posit-dev/connect-extensions/releases).
2. Remove the associated tag from the [GitHub Tags page](https://github.com/posit-dev/connect-extensions/tags).

### Removing an entire piece of content

Removing an entire piece of content from the gallery is similar to removing a single release, but
with a few additional notes:

- Instead of removing a single list from the content list in `extension.json`
  remove the entire content object.
- Instead of reverting the `version` in the `manifest.json` file to the previous
  release, instead set the version to `0.0.0` to avoid a release.

And after the pull request is merged:

- Remove all associated releases for the content from the [GitHub Releases page](https://github.com/posit-dev/connect-extensions/releases).
- Remove all associated tags for the content from the [GitHub Tags page](https://github.com/posit-dev/connect-extensions/tags).

## Removing Content

Removing content from the `extensions/` subdirectory that has already been
added to the Connect Gallery requires that you follow instructions in the
above [Removing an entire piece of content](#removing-an-entire-piece-of-content)
section.

In addition references to the content in GitHub workflows will need to removed.

## Using a CHANGELOG

It is recommended to use a `CHANGELOG.md` file in your extension directory
to document changes made on each release.

A recommended format is the [keep a changelog](https://keepachangelog.com/en/1.1.0/)
format and ahering to the [Semantic Versioning](https://semver.org/) guidelines.
