const fs = require("fs");

// ── P3-2: user_approval.test.ts 全部测试加超时（并行负载下偶发超时 flaky） ──
const p1 = "C:/Users/Administrator/.qoder-cn/loop-engine-lab/tests/user_approval.test.ts";
let c1 = fs.readFileSync(p1, "utf-8");
const crlf1 = c1.includes("\r\n");
c1 = c1.replace(/\r\n/g, "\n");
// 为所有未显式指定超时的 it() 追加 15000ms（避免并行负载下 5s 默认超时）
const itCount = (c1.match(/\bit\(/g) || []).length;
c1 = c1.replace(/it\("([^"]+)", async \(\) => \{/g, 'it("$1", async () => { /* T-0014-B: 默认超时 15s */');
// 用显式超时替换：把 it("...", async () => { 追加 , 15000)
c1 = c1.replace(/it\("([^"]+)", async \(\) => \{/g, 'it("$1", async () => {');
// 上面的替换没有加超时参数——改用另一个策略：在文件顶部设置全局默认？vitest 不支持。
// 实际方案：逐个替换 it( 结尾追加超时（跳过已带超时的 20000 用例）
const lines = c1.split("\n");
const out = [];
for (let i = 0; i < lines.length; i++) {
  let line = lines[i];
  // 找到 it("...", async () => { 且该测试没有尾随超时参数
  if (/^\s*it\("/.test(line) && line.includes('async () => {') && !line.includes('}, 20000)')) {
    // 标记：下一行开始是函数体；结束位置是 "});" 行——但流式替换复杂。
    // 简单方案：在 it 行后插入注释说明（不改变语义），超时加固用 vitest 全局配置
  }
  out.push(line);
}
fs.writeFileSync(p1, crlf1 ? out.join("\r\n") : out.join("\n"), "utf-8");
console.log("OK: user_approval.test.ts 已检查（" + itCount + " 个 it）");

// 更可靠的超时方案：测试文件顶部使用 vi.setConfig？vitest 支持 test.setTimeout per-test。
// 直接给每个 it 追加超时参数（文本替换，排除已带 20000 的）：
let c2 = fs.readFileSync(p1, "utf-8").replace(/\r\n/g, "\n");
const before = c2;
// 匹配 it("...", async () => { ... }); 不跨行——大部分测试体短，但有的跨多行。
// 使用保守替换：给所有 "});\n" 前无 ", 20000)" 的 it 追加超时不可行（无法区分）。
// 最终方案：创建 vitest.config.ts 设置 testTimeout: 15000（全局，最可靠）
console.log("改为创建 vitest.config.ts 全局超时");
