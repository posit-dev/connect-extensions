.DEFAULT_GOAL := help

# Shell settings
SHELL := /bin/bash

# Use an empty target to force running every time
.PHONY: FORCE
FORCE:

# Creating extensions
DIR:=
create-extension:  ## [ext] Create extension folder
	@if [ -z "$(DIR)" ]; then \
		echo 'Please provide a directory name using `make create-extension DIR="my_dir"'; \
		exit 1; \
	fi
	@# If the directory contains a slash, error
	@if echo $(DIR) | grep -q '/'; then \
		echo 'Please provide a directory name without a slash'; \
		exit 1; \
	fi
	@# If the directory already exists, error
	@if [ -d "extensions/$(DIR)" ]; then \
		echo 'Directory "extensions/$(DIR)" already exists'; \
		exit 1; \
	fi

	@echo "🔧 Creating directory: extensions/$(DIR)"
	@mkdir -p "extensions/$(DIR)"

	@echo ""
	@echo "⏳ Remaining Tasks:"
	@echo "- [ ] Copy in app files"
	@echo "- [ ] Create manifest.json"


# build: FORCE   ## [py] Build python package
# 	@echo "🧳 Building python package"
# 	@[ -d dist ] && rm -r dist || true
# 	uv build

help: FORCE  ## Show help messages for make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; { \
		printf "\033[32m%-18s\033[0m", $$1; \
		if ($$2 ~ /^\[docs\]/) { \
			printf "\033[34m[docs]\033[0m%s\n", substr($$2, 7); \
		} else if ($$2 ~ /^\[py\]/) { \
			printf "  \033[33m[py]\033[0m%s\n", substr($$2, 5); \
		} else if ($$2 ~ /^\[ext\]/) { \
			printf " \033[35m[ext]\033[0m%s\n", substr($$2, 6); \
		} else if ($$2 ~ /^\[r\]/) { \
			printf "   \033[31m[r]\033[0m%s\n", substr($$2, 4); \
		} else { \
			printf "       %s\n", $$2; \
		} \
	}'
