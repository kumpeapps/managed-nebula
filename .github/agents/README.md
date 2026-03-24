# Using the Managed Nebula Integration Agent

This directory contains a reusable Copilot agent that can be copied to other repositories to help developers integrate with or extend Managed Nebula.

## Quick Setup

### Option 1: Copy to Your Repository

1. **Copy the agent file** to your repository:
   ```bash
   mkdir -p .github/agents
   cp managed-nebula-integration.agent.md /path/to/your/repo/.github/agents/
   ```

2. **Activate in VS Code**: The agent will be automatically discovered by GitHub Copilot when you open the workspace.

3. **Use the agent**: In Copilot Chat, mention the agent:
   ```
   @managed-nebula How do I create a client using the API?
   ```

### Option 2: Direct Link (for quick reference)

If you don't want to copy the file, you can keep this repository open in VS Code alongside your project, and the agent will still be available.

## Agent Capabilities

The `managed-nebula` agent can help you with:

### 🔌 **API Integration**
- REST API authentication (session-based and API keys)
- Client provisioning automation
- Group and firewall management
- Complete code examples in Python

### 🤖 **Client Setup**
- Docker-based client deployment
- Token-based authentication
- Configuration management
- Multi-platform support (Docker, Windows, macOS)

### 🔒 **Security Best Practices**
- API key management and rotation
- Secure credential storage
- Rate limiting and retry logic
- Error handling patterns

### 🛠️ **Common Patterns**
- Bulk operations (create/update many clients)
- Health monitoring and status checks
- Dynamic firewall rule management
- Group-based access control

### 📊 **Testing & Development**
- Integration test templates
- Environment-specific configuration
- Mock data and fixtures
- CI/CD integration examples

## Example Usage

### Creating a Client Provisioning script

**You:** `@managed-nebula I need to write a Python script that creates 10 new Nebula clients and assigns them to a specific group. How should I structure this?`

**Agent Response:** Provides complete code with:
- API key authentication setup
- Bulk client creation with error handling
- Group assignment logic
- Usage tracking and logging

### Setting Up Monitoring

**You:** `@managed-nebula How can I monitor my Nebula network health and get alerts when clients haven't connected?`

**Agent Response:** Provides:
- Health check API calls
- Metrics collection patterns
- Alert threshold suggestions
- Complete monitoring script template

### Building a Terraform Provider

**You:** `@managed-nebula I'm building a Terraform provider for Managed Nebula. What endpoints should I focus on and what's the proper CRUD pattern?`

**Agent Response:** Provides:
- Resource mapping (clients, groups, firewall rules, etc.)
- CRUD operation patterns for each resource type
- State management considerations
- Error handling specific to Terraform

## Advanced Usage

### Combining with Other Agents

The agent works well alongside other specialized agents:

```
@managed-nebula @security How should I securely store Managed Nebula API keys in my Kubernetes cluster?
```

### Agent in CI/CD Pipelines

Use the agent to help build GitHub Actions or GitLab CI workflows:

```
@managed-nebula Create a GitHub Actions workflow that provisions a new Nebula client on every deployment to staging
```

### Integration Testing

Get help writing comprehensive tests:

```
@managed-nebula Write pytest fixtures for testing Managed Nebula API integration
```

## What's Included

The agent has comprehensive knowledge of:

- ✅ **Complete API Reference**: All endpoints with request/response schemas
- ✅ **Authentication Types**: Sessions, API keys, client tokens
- ✅ **Best Practices**: Security, error handling, rate limiting
- ✅ **Code Examples**: Python, JavaScript/Node.js, curl
- ✅ **Common Patterns**: Provisioning, monitoring, firewall management
- ✅ **Error Solutions**: Troubleshooting common integration issues
- ✅ **Testing Templates**: Unit and integration test examples

## Customization

You can customize the agent for your specific needs:

1. **Edit the agent file** to add project-specific patterns
2. **Add custom examples** relevant to your use case
3. **Include environment-specific details** (URLs, naming conventions)
4. **Extend with additional tools** your team uses

Example: Add your company's naming conventions:

```markdown
## Company-Specific Guidelines

### Naming Convention
All Nebula clients must follow the pattern: `{environment}-{service}-{region}`

Example: `prod-api-us-east-1`

```python
def create_company_client(service: str, environment: str, region: str):
    name = f"{environment}-{service}-{region}"
    # ... rest of implementation
```

## Updating the Agent

When Managed Nebula adds new features:

1. Pull the latest version from the main repository
2. Review changes in the agent file
3. Merge relevant updates into your customized version
4. Test with your specific use cases

## Troubleshooting

### Agent Not Showing Up

- **Check file location**: Should be in `.github/agents/` directory
- **Check file extension**: Must be `.agent.md`
- **Restart VS Code**: Sometimes needed for discovery
- **Check Copilot version**: Requires recent GitHub Copilot version

### Agent Giving Generic Answers

The agent is context-aware. Be specific:

❌ **Too generic**: "How do I use the API?"
✅ **Better**: "Show me how to create a client using the Python API with error handling"

### Agent Not Using Latest Features

Make sure you're using the latest version of the agent file from the main repository.

## Real-World Use Cases

### 1. Kubernetes Operator

```
@managed-nebula I'm building a Kubernetes operator that manages Nebula clients 
as CRDs. What's the reconciliation pattern I should use?
```

### 2. CLI Tool

```
@managed-nebula Help me design a CLI tool (like `kubectl` but for Nebula) with 
commands for client management, group operations, and status checks
```

### 3. Monitoring Dashboard

```
@managed-nebula I need to build a Grafana dashboard that shows Nebula network 
health. What metrics should I collect from the API?
```

### 4. Terraform Provider

```
@managed-nebula Create a Terraform resource definition for managing Nebula 
clients with proper state management and drift detection
```

### 5. GitOps Workflow

```
@managed-nebula Design a GitOps workflow where Nebula network configuration is 
stored in Git and automatically applied via CI/CD
```

## Contributing

If you develop useful patterns or improvements:

1. Consider contributing back to the main repository
2. Share your custom extensions with the community
3. Report issues or missing features in the GitHub repo

## Resources

- **Main Repository**: https://github.com/kumpeapps/managed-nebula
- **API Documentation**: See `API_KEY_GUIDE.md` in the main repo
- **Docker Images**: `ghcr.io/kumpeapps/managed-nebula/{server,frontend,client}:latest`
- **Nebula Docs**: https://github.com/slackhq/nebula

## License

This agent is part of the Managed Nebula project and follows the same MIT license.

Feel free to copy, modify, and distribute for your integration needs!
