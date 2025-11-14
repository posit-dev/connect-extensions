import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import fs from "fs";
import {
  getExtensionNameFromRelease,
  ExtensionList,
  main,
} from "./extension-list";
import {
  ExtensionManifest,
  ExtensionVersion,
} from "./types";

// mock fs module
vi.mock("fs");

const mockFs = fs as any;

describe("extension-list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getExtensionNameFromRelease", () => {
    it("should extract extension name from tag", () => {
      const release = { tag_name: "my-extension@1.0.0" };
      expect(getExtensionNameFromRelease(release)).toBe("my-extension");
    });
  });

  describe("ExtensionList", () => {
    let extensionList: ExtensionList;

    beforeEach(() => {
      extensionList = new ExtensionList([], [], [], []);
    });

    describe("addRelease", () => {
      it("should add release to new extension", () => {
        const manifest: ExtensionManifest = {
          extension: {
            name: "test-ext",
            title: "Test Extension",
            description: "Test description",
            homepage: "https://example.com",
            version: "1.0.0",
            minimumConnectVersion: "2024.01.0",
          },
        };

        const githubRelease = {
          published_at: "2024-01-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/test-ext.tar.gz",
            },
          ],
        };

        extensionList.addRelease(manifest, githubRelease);

        expect(extensionList.extensions).toHaveLength(1);
        expect(extensionList.extensions[0].name).toBe("test-ext");
        expect(extensionList.extensions[0].latestVersion.version).toBe("1.0.0");
      });

      it("should add new version to existing extension", () => {
        const manifest: ExtensionManifest = {
          extension: {
            name: "test-ext",
            title: "Test Extension",
            description: "Test",
            homepage: "https://example.com",
            version: "1.0.0",
            minimumConnectVersion: "2024.01.0",
          },
        };

        const release1 = {
          published_at: "2024-01-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/1.0.0.tar.gz",
            },
          ],
        };

        extensionList.addRelease(manifest, release1);

        const manifest2 = {
          ...manifest,
          extension: { ...manifest.extension, version: "1.1.0" },
        };
        const release2 = {
          published_at: "2024-02-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/1.1.0.tar.gz",
            },
          ],
        };

        extensionList.addRelease(manifest2, release2);

        const extension = extensionList.getExtension("test-ext");
        expect(extension?.versions).toHaveLength(2);
        expect(extension?.latestVersion.version).toBe("1.1.0");
      });
    });

    describe("addExtensionVersion", () => {
      it("should throw error for invalid semver", () => {
        const initialVersion: ExtensionVersion = {
          version: "1.0.0",
          released: "2024-01-01",
          url: "https://example.com/1.0.0.tar.gz",
          minimumConnectVersion: "2024.01.0",
        };

        extensionList.addNewExtension(
          "test-ext",
          "Test",
          "Test",
          "https://example.com",
          initialVersion
        );

        const invalidVersion: ExtensionVersion = {
          version: "invalid-version",
          released: "2024-01-01",
          url: "https://example.com/invalid.tar.gz",
          minimumConnectVersion: "2024.01.0",
        };

        expect(() =>
          extensionList.addExtensionVersion("test-ext", invalidVersion)
        ).toThrow("Invalid version: invalid-version");
      });

      it("should throw error for duplicate version", () => {
        const initialVersion: ExtensionVersion = {
          version: "1.0.0",
          released: "2024-01-01",
          url: "https://example.com/1.0.0.tar.gz",
          minimumConnectVersion: "2024.01.0",
        };

        extensionList.addNewExtension(
          "test-ext",
          "Test",
          "Test",
          "https://example.com",
          initialVersion
        );

        const duplicateVersion: ExtensionVersion = {
          version: "1.0.0",
          released: "2024-01-15",
          url: "https://example.com/1.0.0-new.tar.gz",
          minimumConnectVersion: "2024.01.0",
        };

        expect(() =>
          extensionList.addExtensionVersion("test-ext", duplicateVersion)
        ).toThrow("Version 1.0.0 already exists");
      });
    });
  });

  describe("main (prerelease routing)", () => {
    const originalEnv = process.env;

    beforeEach(() => {
      vi.resetModules();
      process.env = { ...originalEnv };
    });

    afterEach(() => {
      process.env = originalEnv;
    });

    it("should write to extensions.json by default", () => {
      const mockData = {
        categories: [],
        tags: [],
        requiredFeatures: [],
        extensions: [],
      };

      mockFs.readFileSync.mockImplementation((path: string) => {
        if (path.includes("manifest.json")) {
          return JSON.stringify({
            extension: {
              name: "test-ext",
              title: "Test Extension",
              description: "Test",
              homepage: "https://example.com",
              version: "1.0.0",
              minimumConnectVersion: "2024.01.0",
            },
          });
        }
        return JSON.stringify(mockData);
      });

      mockFs.writeFileSync.mockImplementation(() => {});

      process.env.RELEASES = JSON.stringify([
        {
          tag_name: "test-ext@1.0.0",
          published_at: "2024-01-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/test-ext.tar.gz",
            },
          ],
        },
      ]);

      main();

      // Check that writeFileSync was called with a path ending in extensions.json
      expect(mockFs.writeFileSync).toHaveBeenCalled();
      const writePath = mockFs.writeFileSync.mock.calls[0][0];
      expect(writePath).toContain("extensions.json");
      expect(writePath).not.toContain("extensions-prerelease.json");
    });

    it("should write to extensions-prerelease.json when EXTENSION_LIST_FILE is set", () => {
      const mockData = {
        categories: [],
        tags: [],
        requiredFeatures: [],
        extensions: [],
      };

      mockFs.readFileSync.mockImplementation((path: string) => {
        if (path.includes("manifest.json")) {
          return JSON.stringify({
            extension: {
              name: "test-ext",
              title: "Test Extension",
              description: "Test",
              homepage: "https://example.com",
              version: "1.0.0-beta.1",
              minimumConnectVersion: "2024.01.0",
            },
          });
        }
        return JSON.stringify(mockData);
      });

      mockFs.writeFileSync.mockImplementation(() => {});

      process.env.EXTENSION_LIST_FILE = "extensions-prerelease.json";
      process.env.RELEASES = JSON.stringify([
        {
          tag_name: "test-ext@1.0.0-beta.1",
          published_at: "2024-01-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/test-ext.tar.gz",
            },
          ],
        },
      ]);

      main();

      // Check that writeFileSync was called with a path ending in extensions-prerelease.json
      expect(mockFs.writeFileSync).toHaveBeenCalled();
      const writePath = mockFs.writeFileSync.mock.calls[0][0];
      expect(writePath).toContain("extensions-prerelease.json");
    });

    it("should process prerelease versions correctly", () => {
      const mockData = {
        categories: [],
        tags: [],
        requiredFeatures: [],
        extensions: [],
      };

      mockFs.readFileSync.mockImplementation((path: string) => {
        if (path.includes("manifest.json")) {
          return JSON.stringify({
            extension: {
              name: "test-ext",
              title: "Test Extension",
              description: "Test",
              homepage: "https://example.com",
              version: "1.0.0-beta.1",
              minimumConnectVersion: "2024.01.0",
            },
          });
        }
        return JSON.stringify(mockData);
      });

      mockFs.writeFileSync.mockImplementation(() => {});

      process.env.EXTENSION_LIST_FILE = "extensions-prerelease.json";
      process.env.RELEASES = JSON.stringify([
        {
          tag_name: "test-ext@1.0.0-beta.1",
          published_at: "2024-01-01T00:00:00Z",
          assets: [
            {
              name: "test-ext.tar.gz",
              browser_download_url: "https://example.com/test-ext.tar.gz",
            },
          ],
        },
      ]);

      main();

      expect(mockFs.writeFileSync).toHaveBeenCalled();
      const writeCall = mockFs.writeFileSync.mock.calls[0];
      const writtenData = JSON.parse(writeCall[1]);

      // Verify the prerelease version was added
      expect(writtenData.extensions).toHaveLength(1);
      expect(writtenData.extensions[0].name).toBe("test-ext");
      expect(writtenData.extensions[0].latestVersion.version).toBe("1.0.0-beta.1");
    });
  });
});
