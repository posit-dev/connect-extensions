export interface ExtensionManifest {
  extension: {
    name: string;
    title: string;
    description: string;
    homepage: string;
    version: string;
    minimumConnectVersion: string;
    tags?: string[];
  };
}

export interface ExtensionVersion {
  version: string;
  released: string;
  url: string;
  minimumConnectVersion: string;
}

export interface Extension {
  name: string;
  title: string;
  description: string;
  homepage: string;
  latestVersion: ExtensionVersion;
  versions: ExtensionVersion[];
  tags: string[];
}
