# Makefile for ManagedNebula macOS Client

.PHONY: all build clean install test run help

# Build configuration
BUILD_DIR = .build
BINARY_NAME = ManagedNebula
INSTALL_PATH = /usr/local/bin

all: build

help:
	@echo "ManagedNebula macOS Client - Build Targets"
	@echo ""
	@echo "  make build    - Build release binary"
	@echo "  make debug    - Build debug binary"
	@echo "  make clean    - Clean build artifacts"
	@echo "  make run      - Build and run the application"
	@echo "  make install  - Install to /usr/local/bin (requires sudo)"
	@echo "  make test     - Run tests"
	@echo ""

build:
	@echo "Building ManagedNebula (release)..."
	swift build -c release
	@echo "Build complete: $(BUILD_DIR)/release/$(BINARY_NAME)"

debug:
	@echo "Building ManagedNebula (debug)..."
	swift build
	@echo "Build complete: $(BUILD_DIR)/debug/$(BINARY_NAME)"

clean:
	@echo "Cleaning build artifacts..."
	swift package clean
	rm -rf $(BUILD_DIR)

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
