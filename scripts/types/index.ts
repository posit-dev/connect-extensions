export interface ExtensionManifest {
  extension: {
    name: string;
    title: string;
    description: string;
    homepage: string;
    version: string;
    minimumConnectVersion: string;
    requiredFeatures?: RequiredFeature[];
    tags?: string[];
  };
}

export enum RequiredFeature {
  API_PUBLISHING = 'API Publishing',
  OAUTH_INTEGRATIONS = 'OAuth Integrations',
  CURRENT_USER_EXECUTION = 'Current User Execution',
}

export interface ExtensionVersion {
  version: string;
  released: string;
  url: string;
  minimumConnectVersion: string;
  requiredFeatures?: RequiredFeature[];
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
