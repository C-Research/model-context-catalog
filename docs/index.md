# Model Context Catalog

MCC is an MCP (Model Context Protocol) server that acts as a permission-controlled catalog of Python tools. It lets you expose arbitrary Python functions to Claude and other LLM clients through a unified `search` / `execute` interface, with authentication and RBAC built in.

## How it works

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client (Claude)               │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP (MCP protocol)
┌───────────────────────▼─────────────────────────────┐
│                    MCC Server                        │
│                                                      │
│   search(query, group)    execute(name, params)      │
└──────────┬────────────────────────┬─────────────────┘
           │                        │
    ┌──────▼──────┐         ┌───────▼───────┐
    │  Tool Catalog│         │  Auth / RBAC  │
    │  (YAML files)│         │  (ES + groups)│
    └─────────────┘         └───────────────┘
```

The LLM uses two tools:

- **`search(query)`** — finds tools by natural language (hybrid keyword + semantic search), returns signatures with relevance scores
- **`execute(name, params)`** — runs a tool by key, validates params, checks permissions

## Key features

- Define tools in YAML — point at any Python callable
- Group-based access control with per-user overrides
- Hybrid semantic + keyword search powered by Elasticsearch
- Auth via GitHub OAuth, GitHub PAT, or dev mode
- Hot reload without restarting the server
- Environment variable substitution in YAML configs

## Next steps

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [YAML Tool Format](tools/yaml-format.md)
