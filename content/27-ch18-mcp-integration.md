---
title: "Chapter 18 — MCP Integration: The Model Context Protocol"
part: "Part III — Lemura Framework Deep Dive"
chapter: 18
page: 27
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 18 — MCP Integration: The Model Context Protocol

> *"MCP is to agents what HTTP is to the web — a protocol that lets things talk to each other without knowing each other."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the Model Context Protocol, how to connect Lemura to MCP servers, how to use `MCPClient` and `MCPClientRegistry`, and how to design your own MCP server.

---

### 18.1 What Is the Model Context Protocol?

#### 18.1.1 The Problem MCP Solves

Before MCP, every agent framework implemented its own tool integration layer. Tools written for LangChain did not work in raw API agents. Tools written for one team's internal framework could not be shared with another team using a different stack. The ecosystem of available tools was fragmented by implementation — good tools existed, but integrating them required bespoke glue code for each framework.

MCP (Model Context Protocol) is an open standard that decouples tool implementations from agent frameworks. An MCP server exposes a set of tools via a simple JSON-RPC interface. Any MCP client — including Lemura — can discover those tools and call them without knowing anything about their implementation.

<!-- Accurate as of 2026-03 — verify before next edition -->

#### 18.1.2 MCP vs. Custom Tool APIs

Custom tools (implemented as `IToolDefinition` objects in Lemura) are the right choice when:
- The tool has domain-specific logic that is tightly coupled to your application
- The tool needs direct access to your database, file system, or in-process state
- The tool's behavior needs to change based on session context

MCP server tools are the right choice when:
- The tool provides general-purpose capability (web search, file system, code execution)
- The tool needs to be usable from multiple agent frameworks or multiple teams
- A maintained MCP server already exists for the capability you need

The two approaches compose naturally: a Lemura session can have both custom tools registered via `session.tools.register()` and MCP-sourced tools connected via `mcpServers` configuration.

#### 18.1.3 The MCP Ecosystem in 2026

As of early 2026, the MCP ecosystem includes dozens of published servers: web search, browser automation, file system access, calendar and email integration, database connectors, code execution sandboxes, and domain-specific tools for developer workflows. Before building a custom tool for general-purpose capabilities, check whether an MCP server exists. Using a maintained MCP server saves development time and gives you automatic updates.

<!-- Accurate as of 2026-03 — verify before next edition -->

### 18.2 MCP Architecture

#### 18.2.1 The Client-Server Model

MCP uses a client-server architecture. The server exposes tools as named operations with JSON Schema parameters. The client discovers available tools, formats tool call requests according to the schema, sends them to the server, and receives results.

In Lemura, `MCPClient` is the low-level client for a single server, and `MCPClientRegistry` manages multiple servers. `SessionManager` creates the registry automatically when `mcpServers` is configured.

#### 18.2.2 Transports: stdio, SSE, WebSocket

MCP servers communicate via three transport mechanisms:

- **`stdio`**: The client spawns the server as a child process and communicates over stdin/stdout. Best for local processes, development tools, and CLI-wrapped services.
- **`http` / `sse`**: The server runs as a remote HTTP service. The client connects to a URL and communicates over server-sent events (SSE). Best for shared services and cloud-hosted tools.
- **`websocket`**: Bidirectional WebSocket transport. Less common; used when the server needs to push events to the client.

Most ecosystem MCP servers support `stdio` for local use and `http`/`sse` for production deployment.

#### 18.2.3 Capability Negotiation

When a client connects to an MCP server, the first exchange is capability negotiation: the server declares what it supports (tools, prompts, resources) and the client acknowledges. Lemura's `MCPClient` uses this to discover the tool list automatically — you do not need to declare what tools a server provides.

### 18.3 Lemura's MCP Support

#### 18.3.1 `MCPClient`: Connecting to a Single Server

`MCPClient` (see `src/mcp/MCPClient.ts`) manages a connection to a single MCP server. It handles connecting, tool discovery, tool execution, reconnection on failure, and disconnection.

```typescript
// Low-level MCPClient usage (usually managed by MCPClientRegistry)
import { MCPClient } from "lemura/mcp";

const client = new MCPClient(
  "filesystem",
  { transport: "stdio", command: "npx", args: ["@modelcontextprotocol/server-filesystem", "/workspace"] },
  logger,
);

await client.connect();
console.log(client.tools.map(t => t.name)); // ['read_file', 'write_file', ...]

const result = await client.callTool("read_file", { path: "/workspace/README.md" });
await client.disconnect();
```

`client.tools` is available after `connect()` and contains the tool definitions discovered from the server. `client.isConnected` reflects the current connection state.

#### 18.3.2 `MCPClientRegistry`: Managing Multiple Servers

`MCPClientRegistry` (see `src/mcp/MCPClientRegistry.ts`) manages a collection of `MCPClient` instances. It handles connecting all servers, deduplicating tool names across servers (with namespacing), routing tool calls to the correct server, and bulk disconnection.

`SessionManager` creates and manages an `MCPClientRegistry` internally when `mcpServers` is configured. You rarely interact with it directly.

#### 18.3.3 Automatic Tool Discovery

When a session connects to MCP servers, it calls `registry.discoverTools()` to get the full list of tools from all connected servers. These tools are registered in the session's `ToolRegistry` with their server name as a namespace prefix (configurable). The model sees them as regular tools.

### 18.4 Connecting to an MCP Server

#### 18.4.1 stdio Transport: Local Processes

```typescript
// Session with a local MCP filesystem server via stdio
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 80_000,
  mcpServers: [
    {
      name: "filesystem",
      transport: "stdio",
      command: "npx",
      args: [
        "@modelcontextprotocol/server-filesystem",
        "/workspace/project",   // root directory the server can access
      ],
    },
  ],
});

// Tools from the filesystem server are automatically available
const result = await session.run("List all TypeScript files in the project.");
```

The `command` and `args` specify how to launch the server process. The server runs as a child process of your Node.js application.

#### 18.4.2 HTTP/SSE Transport: Remote Servers

```typescript
// Session connecting to a remote MCP server over HTTP/SSE
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 80_000,
  mcpServers: [
    {
      name: "web_search",
      transport: "sse",
      url: "https://mcp.search-provider.example.com/sse",
      timeoutMs: 15_000,
    },
  ],
});
```

Remote servers need a `url`. Authentication is handled via the `env` field for `stdio` servers (passing API keys as environment variables) or via HTTP headers for remote servers (if the server's transport layer supports them).

#### 18.4.3 Authentication

For `stdio` servers that need credentials:

```typescript
// Passing credentials to an MCP server via environment variables
{
  name: "github",
  transport: "stdio",
  command: "npx",
  args: ["@modelcontextprotocol/server-github"],
  env: { GITHUB_TOKEN: process.env.GITHUB_TOKEN! },
}
```

The `env` field merges the specified variables with the child process's environment. Only pass the credentials the server needs — do not forward the entire parent process environment.

### 18.5 Using MCP Tools in a Session

#### 18.5.1 Auto-Registration

When a session with `mcpServers` runs for the first time, `SessionManager` connects all configured servers and calls `discoverTools()`. The discovered tools are registered in the `ToolRegistry` alongside any custom tools. From the model's perspective, there is no difference between a custom tool and an MCP tool.

#### 18.5.2 Tool Namespacing

When multiple MCP servers are configured and their tool names conflict, Lemura namespaces the tools with the server name: `filesystem__read_file` instead of `read_file`. You can also configure a custom namespace prefix per server.

Check connected tool names after construction if you are unsure which server a tool comes from:

```typescript
// Inspecting registered tools after MCP connection
await session.run(""); // triggers MCP connection
const tools = session.tools.getAll();
console.log(tools.map(t => t.name));
// ['filesystem__read_file', 'filesystem__list_dir', 'search_web', ...]
```

#### 18.5.3 Filtering Available Tools

Not every tool from every MCP server needs to be available in every session. Expose only the tools the agent needs for the current task. Use `session.tools.unregister()` to remove tools after connection, or configure server-specific tool filters if the server supports capability filtering during negotiation.

A session with 40 tools has a higher tool-calling error rate than a session with 10 well-chosen tools. The model must select from everything available; a crowded tool set increases the chance of wrong selections.

### 18.6 Building Your Own MCP Server

#### 18.6.1 When to Build vs. Use Existing

Build a custom MCP server when:
- You need to expose internal company tools to multiple agent projects
- The capability does not exist in the public MCP ecosystem
- You want to version and deploy tool implementations independently from agent code

Use existing MCP servers when they exist and are maintained. The MCP ecosystem is growing rapidly; what was not available six months ago may be available now.

#### 18.6.2 The MCP Server Structure

An MCP server implements a few core methods: tool listing (returning tool name, description, and JSON Schema), tool execution (receiving name and arguments, returning a result), and optionally prompts and resources. The MCP specification defines the exact JSON-RPC envelope.

For TypeScript, the `@modelcontextprotocol/sdk` package provides a server scaffold that handles the protocol mechanics — you implement the domain logic:

```typescript
// Minimal MCP server with one tool, using the official SDK
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-internal-tools",
  version: "1.0.0",
});

server.tool(
  "get_team_oncall",
  "Returns the current on-call engineer for a team.",
  { team: z.string().describe("Team name (e.g. 'payments', 'infra')") },
  async ({ team }) => {
    const engineer = await lookupOncall(team); // your domain logic
    return { content: [{ type: "text", text: engineer }] };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

#### 18.6.3 Testing Your Server with Lemura

Test your MCP server by connecting it to a Lemura session and verifying that tool discovery works and tool calls return expected results:

```typescript
// Integration test: connect a local MCP server and verify tool behavior
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 50_000,
  mcpServers: [{
    name: "my_tools",
    transport: "stdio",
    command: "node",
    args: ["dist/mcp-server.js"],
  }],
});

const result = await session.run(
  "Who is on-call for the payments team right now?"
);
console.assert(result.includes("engineer name")); // verify the tool was called
```

### 18.7 MCP in Production

#### 18.7.1 Server Lifecycle Management

In production, MCP server processes need lifecycle management: they must start before the session uses them and stop after. For `stdio` servers, `MCPClient` handles the child process lifecycle automatically. For `http`/`sse` servers, ensure the server is running before the session connects.

When `session.close()` is called, `SessionManager` calls `registry.disconnectAll()`, which gracefully closes all server connections. Always call `session.close()` when a session is done — resource leaks from unclosed server connections accumulate in long-running processes.

#### 18.7.2 Error Handling and Reconnection

Network failures and server crashes cause MCP connections to drop. Lemura's `MCPClient` logs the error and marks the connection as unhealthy. Tool calls routed to a disconnected server return a structured error: `{ error: true, message: "MCP server unavailable: ..." }`. The model receives this and can decide whether to retry or abort.

For critical MCP servers, implement a health check before starting the session:

```typescript
// Checking server health before accepting production traffic
const client = new MCPClient("critical_server", config, logger);
await client.connect();
if (!client.isConnected) {
  throw new Error("Critical MCP server is unavailable — aborting session");
}
```

#### 18.7.3 Security Considerations

MCP servers execute tool calls with whatever permissions the server process has. A `stdio` MCP server running with file system access can read and write files. A remote MCP server may have access to sensitive internal APIs. Apply the principle of least privilege: configure each server to access only the resources the agent's task requires.

> [!WARNING]
> Never connect an agent to an MCP server that has write access to production systems without implementing a `ToolFirewall` in the session. The model can be manipulated via prompt injection in tool results to call write operations with adversarial arguments. Defense-in-depth requires multiple layers: tool firewall, server-side access controls, and audit logging.

---

## Key Takeaways

- MCP decouples tool implementations from agent frameworks; any MCP-compliant server works with any MCP-compliant client, including Lemura.
- Configure servers in `SessionConfig.mcpServers`; Lemura handles connection, tool discovery, and routing automatically — MCP tools appear alongside custom tools in the session.
- Use `stdio` transport for local development and CLI-wrapped tools; use `http`/`sse` transport for remote, shared services.
- Limit the tools available to the model: a session with 10 well-chosen tools has lower tool-calling error rates than one with 40 tools from multiple servers.
- Always call `session.close()` in production to release MCP server connections; always implement a `ToolFirewall` for sessions connected to servers with write access to production systems.
