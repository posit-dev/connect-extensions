export interface Category {
  title: string;
  description: string;
}

export interface LanguageRequirement {
  requires: string;
}

export interface ExtensionEnvironment {
  python?: LanguageRequirement;
  r?: LanguageRequirement;
  quarto?: LanguageRequirement;
}

export interface ExtensionManifest {
  extension: {
    name: string;
    title: string;
    description: string;
    homepage: string;
    version: string;
    minimumConnectVersion: string;
    requiredFeatures?: RequiredFeature[];
    category?: Category['title'];
    tags?: string[];
  };
  environment?: ExtensionEnvironment;
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
  requiredEnvironment?: ExtensionEnvironment;
}

export interface Extension {
  name: string;
  title: string;
  description: string;
  homepage: string;
  latestVersion: ExtensionVersion;
  versions: ExtensionVersion[];
  tags: string[];
  category?: string;
}
