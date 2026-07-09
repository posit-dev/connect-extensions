import fs from "fs";
import path from "path";

import semverValid from "semver/functions/valid";
import semverEq from "semver/functions/eq";
import semverRcompare from "semver/functions/rcompare";

import {
  Category,
  Extension,
  ExtensionEnvironment,
  ExtensionManifest,
  ExtensionVersion,
  RequiredFeature
} from "./types";

function getExtensionNameFromRelease(release: any): string {
  const tag = release.tag_name as string;
  return tag.split("@")[0];
}

function getManifest(extensionName: string): ExtensionManifest {
  // Runs from ./scripts/dist so go up an additional level
  const manifestPath = path.join(
    __dirname,
    "..",
    "..",
    "extensions",
    extensionName,
    "manifest.json"
  );
  return JSON.parse(fs.readFileSync(manifestPath, "utf8"));
}

// Node.js content declares its required Node version in package.json's
// `engines.node`, which is the single source of truth Connect reads (it does not
// read a nodejs field from manifest.json). Only nodejs app mode content uses it;
// other extensions may carry a package.json for build tooling, so ignore theirs.
// engines.node is required for nodejs content: Connect needs it to pick a
// runtime, so a nodejs extension without it can't run.
function getEnginesNode(extensionName: string, appmode?: string): string | undefined {
  if (appmode !== "nodejs") {
    return undefined;
  }
  const packageJsonPath = path.join(
    __dirname,
    "..",
    "..",
    "extensions",
    extensionName,
    "package.json"
  );
  if (!fs.existsSync(packageJsonPath)) {
    throw new Error(`Node.js extension ${extensionName} is missing package.json`);
  }
  const pkg = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
  const enginesNode = pkg.engines?.node;
  if (!enginesNode) {
    throw new Error(
      `Node.js extension ${extensionName} must set engines.node in package.json`
    );
  }
  return enginesNode;
}

// Sort the given extension's version in descending order
function sortExtensionVersions(extension: Extension) {
  extension.versions.sort((a, b) => semverRcompare(a.version, b.version));
}

class ExtensionList {
  constructor(
    public categories: Category[],
    public tags: string[],
    public requiredFeatures: RequiredFeature[],
    public extensions: Extension[]
  ) {}

  static fromFile(path: string) {
    const file = JSON.parse(fs.readFileSync(path, "utf8"));
    return new ExtensionList(
      file.categories,
      file.tags,
      file.requiredFeatures,
      file.extensions
    );
  }

  public addRelease(manifest: ExtensionManifest, githubRelease) {
    const {
      name,
      title,
      description,
      homepage,
      version,
      category,
      tags,
      imgUrl,
      minimumConnectVersion,
      requiredFeatures,
    } = manifest.extension;
    const { assets, published_at } = githubRelease;

    const { browser_download_url } = assets.find(
      (asset) => asset.name === `${name}.tar.gz`
    );

    // R/Python/Quarto declare their version range in the manifest environment;
    // Node.js declares its in package.json's `engines.node`. Merge both so the
    // Gallery gets a nodejs requirement the same way it gets the others.
    const enginesNode = getEnginesNode(name, manifest.metadata?.appmode);
    const requiredEnvironment: ExtensionEnvironment = {
      ...(manifest.environment ?? {}),
      ...(enginesNode ? { nodejs: { requires: enginesNode } } : {}),
    };

    const newVersion = {
      version,
      released: published_at,
      url: browser_download_url,
      minimumConnectVersion: minimumConnectVersion,
      ...(requiredFeatures ? { requiredFeatures } : {}),
      ...(Object.keys(requiredEnvironment).length > 0
        ? { requiredEnvironment }
        : {}),
    };

    if (this.getExtension(name)) {
      this.updateExtensionDetails(name, title, description, homepage, tags, category, imgUrl);
      this.addExtensionVersion(name, newVersion);
    } else {
      this.addNewExtension(name, title, description, homepage, newVersion, tags, category, imgUrl);
    }
  }

  public getExtension(name: string): Extension | undefined {
    return this.extensions.find((extension) => extension.name === name);
  }

  private updateExtensionDetails(
    name: string,
    title: string,
    description: string,
    homepage: string,
    tags: string[] = [],
    category?: string,
    imgUrl?: string
  ) {
    this.updateExtension(name, {
      ...this.getExtension(name),
      title,
      description,
      homepage,
      tags,
      ...(category ? { category } : {}),
      ...(imgUrl ? { imgUrl } : {}),
    });
  }

  private addExtensionVersion(name: string, version: ExtensionVersion) {
    const extension = this.getExtension(name);
    if (extension === undefined) {
      throw new Error(`Extension ${name} does not exist in the list`);
    }
    // Check that the version is valid
    if (!semverValid(version.version)) {
      throw new Error(`Invalid version: ${version.version}`);
    }
    // Skip versions that are already recorded.
    if (extension.versions.some((v) => semverEq(v.version, version.version))) {
      console.log(
        `Version ${version.version} already exists for ${name}, skipping.`
      );
      return;
    }

    // Add the version to the list
    extension.versions.push(version);
    sortExtensionVersions(extension);

    // Set the latest version to the newest semver released
    extension.latestVersion = extension.versions[0];

    this.updateExtension(extension.name, extension);
  }

  private addNewExtension(
    name: string,
    title: string,
    description: string,
    homepage: string,
    initialVersion: ExtensionVersion,
    tags: string[] = [],
    category?: string,
    imgUrl?: string
  ) {
    if (this.getExtension(name) !== undefined) {
      throw new Error(`Extension ${name} already exists in the list`);
    }
    this.extensions.push({
      name,
      title,
      description,
      homepage,
      latestVersion: initialVersion,
      versions: [initialVersion],
      tags,
      ...(category ? { category } : {}),
      ...(imgUrl ? { imgUrl } : {}),
    });
  }

  private updateExtension(name: string, data: Extension) {
    const index = this.extensions.findIndex((ex) => ex.name === name);
    if (index === -1) {
      throw new Error(`Failed to update Extension ${name}, not found in list`);
    }
    this.extensions[index] = data;
  }

  public stringify() {
    const output = {
      categories: this.categories,
      tags: this.tags,
      requiredFeatures: this.requiredFeatures,
      extensions: this.extensions
    }
    return JSON.stringify(output, null, 2);
  }

  public sortExtensionsByTitle() {
    this.extensions.sort((a, b) => a.title.localeCompare(b.title));
  }
}

// Runs from ./scripts/dist so go up an additional level
const extensionListFilePath = path.join(
  __dirname,
  "..",
  "..",
  "extensions.json"
);

const releases = JSON.parse(process.env.RELEASES);
const list = ExtensionList.fromFile(extensionListFilePath);

releases.forEach((release) => {
  const name = getExtensionNameFromRelease(release);
  const manifest = getManifest(name);
  list.addRelease(manifest, release);
});

// Always re-sort so any release (new or updated) reorders the whole feed.
list.sortExtensionsByTitle();
fs.writeFileSync(extensionListFilePath, list.stringify());
