export interface ExtensionManifest {
  extension: {
    name: string;
    title: string;
    description: string;
    homepage: string;
    version: string;
  };
}

export interface ExtensionVersion {
  version: string;
  released: string;
  url: string;
}

export interface Extension {
  name: string;
  title: string;
  description: string;
  homepage: string;
  latestVersion: ExtensionVersion;
  versions: ExtensionVersion[];
}
