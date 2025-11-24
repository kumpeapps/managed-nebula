# Makefile for ManagedNebula macOS Client

.PHONY: all build clean install test run help package dmg pkg app-bundle

# Build configuration
BUILD_DIR = .build
BINARY_NAME = ManagedNebula
INSTALL_PATH = /usr/local/bin

all: build

help:
	@echo "ManagedNebula macOS Client - Build Targets"
	@echo ""
	@echo "  make build       - Build release binary"
	@echo "  make debug       - Build debug binary"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make run         - Build and run the application"
	@echo "  make install     - Install to /usr/local/bin (requires sudo)"
	@echo "  make test        - Run tests"
	@echo "  make app-bundle  - Create ManagedNebula.app bundle"
	@echo "  make package     - Create PKG and DMG installers (recommended)"
	@echo "  make pkg         - Create PKG installer only"
	@echo "  make dmg         - Create DMG installer only"
	@echo ""

build:
	@echo "Building ManagedNebula (release)..."
	swift build -c release
	@echo "$${VERSION:-1.0.0}" > $(BUILD_DIR)/release/VERSION
	@echo "Created VERSION file with version: $$(cat $(BUILD_DIR)/release/VERSION)"
	@echo "Build complete: $(BUILD_DIR)/release/$(BINARY_NAME)"

debug:
	@echo "Building ManagedNebula (debug)..."
	swift build
	@echo "$${VERSION:-1.0.0-dev}" > $(BUILD_DIR)/debug/VERSION
	@echo "Created VERSION file with version: $$(cat $(BUILD_DIR)/debug/VERSION)"
	@echo "Build complete: $(BUILD_DIR)/debug/$(BINARY_NAME)"

clean:
	@echo "Cleaning build artifacts..."
	swift package clean
	rm -rf $(BUILD_DIR)
	rm -rf $(BINARY_NAME).app
	rm -rf dist

run: debug
	@echo "Running ManagedNebula..."
	$(BUILD_DIR)/debug/$(BINARY_NAME)

install: build
	@echo "Installing to $(INSTALL_PATH)..."
	@sudo cp $(BUILD_DIR)/release/$(BINARY_NAME) $(INSTALL_PATH)/
	@sudo chmod +x $(INSTALL_PATH)/$(BINARY_NAME)
	@echo "Installation complete"

test:
	@echo "Running tests..."
	swift test

app-bundle: build
	@echo "Creating app bundle..."
	@bash create-app-bundle.sh

package:
	@echo "Creating installers (PKG + DMG)..."
	@bash create-installer.sh
	@echo ""
	@echo "Installers created in dist/ directory"
	@echo "  - Use PKG for complete installation with Nebula binaries"
	@echo "  - Use DMG for drag-and-drop installation (requires Homebrew Nebula)"

pkg: package

dmg: app-bundle
	@echo "Creating DMG installer..."
	@mkdir -p dist/dmg-temp
	@cp -R $(BINARY_NAME).app dist/dmg-temp/
	@ln -s /Applications dist/dmg-temp/Applications
	@hdiutil create -volname "$(BINARY_NAME)" -srcfolder dist/dmg-temp -ov -format UDZO dist/$(BINARY_NAME).dmg
	@rm -rf dist/dmg-temp
	@echo "DMG created: dist/$(BINARY_NAME).dmg"
