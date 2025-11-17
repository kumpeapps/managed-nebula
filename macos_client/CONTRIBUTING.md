# Contributing to ManagedNebula macOS Client

Thank you for your interest in contributing to the ManagedNebula macOS client!

## Development Setup

### Prerequisites

1. **macOS 12 (Monterey) or later**
2. **Xcode 14+ or Swift toolchain**
   ```bash
   xcode-select --install
   # Or download Xcode from App Store
   ```
3. **Nebula binaries** for testing
   ```bash
   curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
   tar xzf nebula-darwin.tar.gz
   sudo mv nebula nebula-cert /usr/local/bin/
   ```

### Building

```bash
# Clone repository
git clone https://github.com/kumpeapps/managed-nebula.git
cd managed-nebula/macos_client

# Build debug version
make debug

# Run from build directory
./.build/debug/ManagedNebula

# Build release version
make build
```

### Project Structure

```
macos_client/
├── Package.swift              # SPM manifest
├── ManagedNebula/Sources/
│   ├── App/                  # Application entry point
│   ├── Services/             # Business logic layer
│   ├── Models/               # Data models
│   └── UI/                   # User interface components
├── README.md                 # User documentation
├── QUICKSTART.md            # Quick start guide
└── CONTRIBUTING.md          # This file
```

## Code Style

### Swift Style Guidelines

- Follow [Swift API Design Guidelines](https://swift.org/documentation/api-design-guidelines/)
- Use 4 spaces for indentation
- Maximum line length: 120 characters
- Use meaningful variable names
- Document public APIs with Swift DocC comments

### Example

```swift
/// Service for managing Nebula daemon lifecycle
class NebulaManager {
    /// Start the Nebula daemon with the current configuration
    /// - Throws: `NebulaError.configNotFound` if configuration file doesn't exist
    /// - Throws: `NebulaError.binaryNotFound` if Nebula binary is not in PATH
    func startNebula() throws {
        // Implementation
    }
}
```

## Making Changes

### Adding New Features

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**
   - Add new files in appropriate directories
   - Update documentation if needed
   - Test thoroughly on macOS

3. **Test locally**
   ```bash
   make build
   ./.build/release/ManagedNebula
   ```

4. **Commit with descriptive messages**
   ```bash
   git commit -m "Add feature: description of what it does"
   ```

5. **Push and create pull request**
   ```bash
   git push origin feature/my-new-feature
   ```

### Fixing Bugs

1. **Create issue if it doesn't exist**
   - Describe the bug
   - Include steps to reproduce
   - Mention macOS version and hardware

2. **Create fix branch**
   ```bash
   git checkout -b bugfix/issue-123-description
   ```

3. **Fix and test**
   - Verify bug is fixed
   - Test on different macOS versions if possible
   - Ensure no regressions

4. **Submit pull request**
   - Reference issue number
   - Describe the fix
   - Include testing notes

## Testing

### Manual Testing Checklist

- [ ] Application launches without errors
- [ ] Menu bar icon appears
- [ ] Preferences window opens and saves settings
- [ ] Token saved to Keychain successfully
- [ ] Keypair generation works
- [ ] Configuration fetch from server succeeds
- [ ] Nebula daemon starts correctly
- [ ] VPN connection established
- [ ] Can ping other Nebula clients
- [ ] Disconnect works properly
- [ ] Check for updates works
- [ ] View logs opens Finder correctly
- [ ] Application quits cleanly

### Testing with Local Server

```bash
# In one terminal, start the Managed Nebula server
cd ../server
docker-compose up

# In another terminal, run the macOS client
cd macos_client
make run

# Configure in preferences:
# - Server URL: http://localhost:8080
# - Token: (generate from web UI at http://localhost)
```

## Common Development Tasks

### Adding a New Service

1. Create file in `ManagedNebula/Sources/Services/`
2. Define class with clear responsibilities
3. Use dependency injection for testability
4. Document public methods

Example:
```swift
// ManagedNebula/Sources/Services/MyService.swift

/// Service for handling specific functionality
class MyService {
    private let dependency: SomeDependency
    
    init(dependency: SomeDependency) {
        self.dependency = dependency
    }
    
    /// Perform the main operation
    func performOperation() throws {
        // Implementation
    }
}
```

### Adding UI Components

1. Create file in `ManagedNebula/Sources/UI/`
2. Use Cocoa/AppKit frameworks
3. Follow macOS Human Interface Guidelines
4. Test on different macOS versions

### Updating Models

1. Edit `ManagedNebula/Sources/Models/Configuration.swift`
2. Maintain `Codable` conformance for persistence
3. Update `default` values if needed
4. Consider migration for breaking changes

## Architecture Guidelines

### Service Layer

Services should:
- Have single responsibility
- Be testable in isolation
- Use protocols for dependencies
- Handle errors appropriately
- Log important operations

### UI Layer

UI components should:
- Be responsive (use async/await for network calls)
- Follow macOS design patterns
- Provide user feedback for long operations
- Handle errors gracefully with user-friendly messages

### Models Layer

Models should:
- Be pure data structures
- Support Codable for serialization
- Have sensible defaults
- Be immutable when possible

## Security Considerations

### Do's ✅

- Use Keychain for sensitive data (tokens, passwords)
- Set proper file permissions (0600 for keys)
- Validate user input
- Use HTTPS for server communication
- Never log sensitive data

### Don'ts ❌

- Don't hardcode credentials
- Don't disable SSL verification
- Don't store passwords in UserDefaults
- Don't expose private keys
- Don't trust server data without validation

## Documentation

### Code Documentation

Use Swift DocC comments for public APIs:

```swift
/// Brief description
///
/// Detailed description explaining what the method does,
/// when to use it, and any important notes.
///
/// - Parameters:
///   - param1: Description of first parameter
///   - param2: Description of second parameter
/// - Returns: Description of return value
/// - Throws: List of errors that can be thrown
func myMethod(param1: String, param2: Int) throws -> Bool {
    // Implementation
}
```

### User Documentation

When adding features:
- Update README.md with usage instructions
- Update QUICKSTART.md if it affects getting started
- Include screenshots for UI changes
- Update troubleshooting section if relevant

## Submitting Pull Requests

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Changes are documented
- [ ] Manual testing completed
- [ ] No hardcoded credentials or sensitive data
- [ ] Commit messages are descriptive
- [ ] PR description explains changes
- [ ] Screenshots included for UI changes

### PR Template

```markdown
## Description
Brief description of changes

## Motivation
Why are these changes needed?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How were the changes tested?

## Screenshots
(if applicable)

## Checklist
- [ ] Tested on macOS 12+
- [ ] Documentation updated
- [ ] No security issues
- [ ] Code reviewed
```

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Documentation**: Check README.md and QUICKSTART.md first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue or discussion if you have questions about contributing!
