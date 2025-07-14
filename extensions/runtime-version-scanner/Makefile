.PHONY: test update-manifest

test:
	Rscript -e 'testthat::test_dir("tests/testthat")'

update-manifest:
	cp manifest.json manifest.old.json
	FILES=$$(jq -r '.files | keys | join(",")' manifest.old.json); \
	Rscript -e "rsconnect::writeManifest(appFiles = strsplit('$$FILES', ',')[[1]])"; \
	jq -n --slurpfile old manifest.old.json --slurpfile new manifest.json \
		'$$new[0] * {"environment": $$old[0].environment, "extension": $$old[0].extension}' \
		> manifest.merged.json
	mv manifest.merged.json manifest.json
	rm manifest.old.json
