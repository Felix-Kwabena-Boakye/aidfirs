# Postman MCP Server Setup

This directory contains the MCP (Model Context Protocol) server configuration for the Postman integration.

## Files

- `blackbox_mcp_settings.json` - BlackBox AI MCP configuration file
- `.vscode/mcp.json` - VS Code MCP configuration file

## Server Name

The server is configured with: **github.com/postmanlabs/postman-mcp-server**

## Configuration Modes

The Postman MCP Server supports three configurations:

1. **Minimal** (Default) - Essential tools for basic Postman operations
2. **Full** - All available Postman API tools (100+ tools)
3. **Code** - Tools for generating client code from API definitions

## Getting Started

### Option 1: Remote Server (Recommended - No local setup needed)

The remote server runs at `https://mcp.postman.com` and uses OAuth or API key authentication.

To use the remote server, add your API key to the configuration:

1. Get a Postman API key from: https://postman.postman.co/settings/me/api-keys
2. Replace `${input:postman-api-key}` with your actual API key

### Option 2: Local Server

The local server runs on your machine using Node.js.

To install locally:

```bash
npm install -g @postman/postman-mcp-server
```

Or use npx:

```bash
npx -y @postman/postman-mcp-server --minimal
```

## Usage

### Remote Server Configuration

The `blackbox_mcp_settings.json` is configured for remote HTTP connection:

```json
{
    "mcpServers": {
        "github.com/postmanlabs/postman-mcp-server": {
            "type": "http",
            "url": "https://mcp.postman.com/minimal",
            "headers": {
                "Authorization": "Bearer YOUR_API_KEY"
            }
        }
    }
}
```

### Local Server Configuration

For local STDIO connection:

```json
{
    "mcpServers": {
        "github.com/postmanlabs/postman-mcp-server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@postman/postman-mcp-server", "--minimal"],
            "env": {
                "POSTMAN_API_KEY": "YOUR_API_KEY"
            }
        }
    }
}
```

## Available Tools (Minimal Mode)

Based on the Postman MCP Server documentation, the minimal mode includes essential tools:

- `listWorkspaces` - List all workspaces
- `getWorkspace` - Get a specific workspace
- `createWorkspace` - Create a new workspace
- `updateWorkspace` - Update a workspace
- `deleteWorkspace` - Delete a workspace
- `listCollections` - List collections
- `getCollection` - Get a specific collection
- `createCollection` - Create a new collection
- `updateCollection` - Update a collection
- `deleteCollection` - Delete a collection
- `listEnvironments` - List environments
- `getEnvironment` - Get a specific environment
- `createEnvironment` - Create a new environment
- `updateEnvironment` - Update an environment
- `deleteEnvironment` - Delete an environment
- `listMocks` - List mocks
- `listMonitors` - List monitors

For full tool list (100+ tools), use `--full` flag instead of `--minimal`.

## Adding to Claude Code / Claude Desktop

```bash
claude mcp add github.com/postmanlabs/postman-mcp-server --env POSTMAN_API_KEY=YOUR_KEY -- npx @postman/postman-mcp-server@latest --minimal
```

## Documentation

For more information, see:
- Postman MCP Server GitHub: https://github.com/postmanlabs/postman-mcp-server
- Postman MCP Server Collection: https://www.postman.com/postman/postman-public-workspace/collection/681dc649440b35935978b8b7
