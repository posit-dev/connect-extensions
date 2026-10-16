.PHONY: update-manifest

# This recipe updates the manifest, with a few helpful modifications:
# - Records Posit Public Package Manager as the package repository, so Connect
#   installs binary packages.
# - Copies over `extension` and `environment` blocks from the old manifest to
#   the new one. These are Gallery-specific blocks, and not created by
#   `rsconnect`.
# - Preserves set of files listed in the `files` block, where
#   `rsconnect::writeManifest()` by default includes all the files in the
#   directory.
update-manifest:
	cp manifest.json manifest.old.json
	FILES=$$(jq -r '.files | keys | join(",")' manifest.old.json); \
	Rscript -e "options(repos = c(CRAN = 'https://packagemanager.posit.co/cran/latest')); rsconnect::writeManifest(appFiles = strsplit('$$FILES', ',')[[1]], appPrimaryDoc = 'index.qmd')"
	jq -n --slurpfile old manifest.old.json --slurpfile new manifest.json \
		'$$new[0] * {"environment": $$old[0].environment, "extension": $$old[0].extension}' \
		> manifest.merged.json
	mv manifest.merged.json manifest.json
	rm manifest.old.json
