import fs from "fs";
import path from "path";

import semverValid from "semver/functions/valid";
import semverEq from "semver/functions/eq";
import semverRcompare from "semver/functions/rcompare";

import { Extension, ExtensionManifest, ExtensionVersion } from "./types";

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

// Sort the given extension's version in descending order
function sortExtensionVersions(extension: Extension) {
  extension.versions.sort((a, b) => semverRcompare(a.version, b.version));
}

class ExtensionList {
  constructor(public tags: string[], public extensions: Extension[]) {
    this.tags = tags;
    this.extensions = extensions;
  }

  static fromFile(path: string) {
    const file = JSON.parse(fs.readFileSync(path, "utf8"));
    return new ExtensionList(file.tags, file.extensions);
  }

  public addRelease(manifest: ExtensionManifest, githubRelease) {
    const {
      name,
      title,
      description,
      homepage,
      version,
      tags,
      minimumConnectVersion,
    } = manifest.extension;
    const { assets, published_at } = githubRelease;

    const { browser_download_url } = assets.find(
      (asset) => asset.name === `${name}.tar.gz`
    );

    const newVersion = {
      version,
      released: published_at,
      url: browser_download_url,
      minimumConnectVersion: minimumConnectVersion,
    };

    if (this.getExtension(name)) {
      this.updateExtensionDetails(name, title, description, homepage, tags);
      this.addExtensionVersion(name, newVersion);
    } else {
      this.addNewExtension(name, title, description, homepage, newVersion, tags);
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
    tags: string[] = []
  ) {
    this.updateExtension(name, {
      ...this.getExtension(name),
      title,
      description,
      homepage,
      tags,
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
    // Check if the version already exists
    if (extension.versions.some((v) => semverEq(v.version, version.version))) {
      throw new Error(`Version ${version.version} already exists`);
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
    tags: string[] = []
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
    });
    this.sortExtensions();
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
      tags: this.tags,
      extensions: this.extensions
    }
    return JSON.stringify(output, null, 2);
  }

  private sortExtensions() {
    this.extensions.sort((a, b) => a.name.localeCompare(b.name));
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

fs.writeFileSync(extensionListFilePath, list.stringify());
