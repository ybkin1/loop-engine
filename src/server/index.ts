import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerTools } from "./tools.js";

const server = new Server(
  { name: "loop-engineering", version: "0.1.0" },
  { capabilities: { tools: {} } },
);

registerTools(server);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[loop-engineering] MCP Server running on stdio");
}

main().catch(err => {
  console.error("[loop-engineering] Fatal:", err);
  process.exit(1);
});
