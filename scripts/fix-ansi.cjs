const fs = require("fs");
const p = "C:/Users/Administrator/.qoder-cn/loop-engine-lab/scripts/quality-gates.ts";
let c = fs.readFileSync(p, "utf-8");
const crlf = c.includes("\r\n");
c = c.replace(/\r\n/g, "\n");

const from = `  // Parse test output
  const testsMatch = result.stdout.match(/Tests\\s+(\\d+)\\s+(?:passed|failed)/);
  const totalMatch = result.stdout.match(/Test Files\\s+\\d+\\s+(?:passed|failed)\\s+\\((\\d+)\\)/);
  const passedMatch = result.stdout.match(/Tests\\s+(\\d+)\\s+passed/);`;

const to = `  // Parse test output（剥离 ANSI 颜色码——vitest 非 TTY 输出含 \\x1b[..m 序列）
  const cleanOut = result.stdout.replace(/\\x1b\\[[0-9;]*m/g, "");
  const testsMatch = cleanOut.match(/Tests\\s+(\\d+)\\s+(?:passed|failed)/);
  const totalMatch = cleanOut.match(/Test Files\\s+\\d+\\s+(?:passed|failed)\\s+\\((\\d+)\\)/);
  const passedMatch = cleanOut.match(/Tests\\s+(\\d+)\\s+passed/);`;

if (!c.includes(from)) {
  console.error("ANCHOR NOT FOUND");
  process.exit(1);
}
c = c.replace(from, to);
fs.writeFileSync(p, crlf ? c.replace(/\n/g, "\r\n") : c, "utf-8");
console.log("DONE: ANSI strip fix");
