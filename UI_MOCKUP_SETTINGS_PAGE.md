# Settings Page UI - Docker Compose Template Editor

## Visual Layout Description

### Page Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  Navbar (with Settings link highlighted)                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Settings                                                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Nebula Configuration                                          │  │
│  │ Global settings that affect all Nebula client configurations │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ ☑ Enable Punchy                                          │ │  │
│  │  │   Nebula "punchy" helps peers behind NAT maintain        │ │  │
│  │  │   connectivity by sending periodic packets.              │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Client Docker Configuration                                   │  │
│  │ Default Docker image and server URL used in generated        │  │
│  │ docker-compose files for clients                             │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ Client Docker Image                                      │ │  │
│  │  │ Full Docker image path                                   │ │  │
│  │  │ [ghcr.io/kumpeapps/managed-nebula-client:latest        ] │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ Server URL                                               │ │  │
│  │  │ URL that clients will use to connect to this server     │ │  │
│  │  │ [http://localhost:8080                                  ] │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Docker Compose Template                                       │  │
│  │ Customize the docker-compose.yml template generated for      │  │
│  │ clients using dynamic placeholders                           │  │
│  │                                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Template Editor          [ Reset to Default ]          │  │  │
│  │  ├────────────────────────────────────────────────────────┤  │  │
│  │  │ version: '3.8'                                         │  │  │
│  │  │                                                         │  │  │
│  │  │ services:                                              │  │  │
│  │  │   nebula-client:                                       │  │  │
│  │  │     image: {{CLIENT_DOCKER_IMAGE}}                    │  │  │
│  │  │     container_name: nebula-{{CLIENT_NAME}}            │  │  │
│  │  │     restart: unless-stopped                            │  │  │
│  │  │     cap_add:                                           │  │  │
│  │  │       - NET_ADMIN                                      │  │  │
│  │  │     devices:                                           │  │  │
│  │  │       - /dev/net/tun                                   │  │  │
│  │  │     environment:                                       │  │  │
│  │  │       SERVER_URL: {{SERVER_URL}}                      │  │  │
│  │  │       CLIENT_TOKEN: {{CLIENT_TOKEN}}                  │  │  │
│  │  │       POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}   │  │  │
│  │  │     volumes:                                           │  │  │
│  │  │       - ./nebula-config:/etc/nebula                   │  │  │
│  │  │       - ./nebula-data:/var/lib/nebula                 │  │  │
│  │  │     network_mode: host                                 │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  Available Placeholders                                       │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Placeholder           Description         Example      │  │  │
│  │  ├────────────────────────────────────────────────────────┤  │  │
│  │  │ {{CLIENT_NAME}}      Client hostname    my-client      │  │  │
│  │  │ {{CLIENT_TOKEN}}     Auth token         abc123...      │  │  │
│  │  │ {{SERVER_URL}}       API endpoint       http://...     │  │  │
│  │  │ {{CLIENT_DOCKER..}}  Docker image       ghcr.io/...    │  │  │
│  │  │ {{POLL_INTERVAL..}}  Polling freq       24             │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  Preview (with sample data)                                   │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ version: '3.8'                                         │  │  │
│  │  │                                                         │  │  │
│  │  │ services:                                              │  │  │
│  │  │   nebula-client:                                       │  │  │
│  │  │     image: ghcr.io/kumpeapps/managed-nebula/...       │  │  │
│  │  │     container_name: nebula-example-client              │  │  │
│  │  │     restart: unless-stopped                            │  │  │
│  │  │     cap_add:                                           │  │  │
│  │  │       - NET_ADMIN                                      │  │  │
│  │  │     devices:                                           │  │  │
│  │  │       - /dev/net/tun                                   │  │  │
│  │  │     environment:                                       │  │  │
│  │  │       SERVER_URL: http://localhost:8080               │  │  │
│  │  │       CLIENT_TOKEN: abc123xyz789...                   │  │  │
│  │  │       POLL_INTERVAL_HOURS: 24                         │  │  │
│  │  │     volumes:                                           │  │  │
│  │  │       - ./nebula-config:/etc/nebula                   │  │  │
│  │  │       - ./nebula-data:/var/lib/nebula                 │  │  │
│  │  │     network_mode: host                                 │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │                                     [ Save Changes ]           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Color Scheme

- **Background**: Light gray (#f5f5f5)
- **Content boxes**: White with subtle shadow
- **Section headers**: Green underline (#4CAF50)
- **Textarea**: Light background with monospace font
- **Placeholders table**: Alternating row colors for readability
- **Code elements**: Green background (#e8f5e9) with green text (#2e7d32)
- **Buttons**:
  - Reset: Orange (#ff9800)
  - Save: Green (#4CAF50)

## Interactive Elements

### Template Editor
- **Textarea**: Resizable, monospace font, syntax-friendly
- **Auto-updates**: Preview updates as you type
- **Validation**: Saves only if YAML is valid

### Reset to Default Button
- **Action**: Replaces current template with default
- **Confirmation**: Shows confirm dialog before resetting
- **Position**: Top-right of editor header

### Placeholders Table
- **Reference**: Quick lookup for available placeholders
- **Columns**: Name, Description, Example value
- **Styling**: Code-style formatting for placeholder names

### Preview Section
- **Live update**: Shows rendered output with sample data
- **Monospace**: Uses code-style formatting
- **Read-only**: Preview cannot be edited directly

### Save Changes Button
- **Position**: Bottom-right of template section
- **Feedback**: Shows success/error notification
- **Validation**: Checks YAML before saving
- **Error handling**: Displays validation errors inline

## Responsive Design

On mobile/tablet devices:
- Sections stack vertically
- Template editor full width
- Table may scroll horizontally
- Buttons stack vertically and expand to full width

## Accessibility Features

- All form elements have proper labels
- Color contrast meets WCAG standards
- Keyboard navigation supported
- Error messages clearly visible
- Focus indicators on interactive elements
