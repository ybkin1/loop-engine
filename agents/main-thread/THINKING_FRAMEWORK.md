# Main-Thread Thinking Framework

## Step 1: 全局视角
- 当前项目处于哪个 phase？哪些 task 是 active？
- 是否有 pending gate 需要用户决策？
- 上次 HANDOFF 的 next step 是什么？

## Step 2: 意图路由
- 用户请求的风险级别？L1/L2/L3？
- 应该进入 LIGHTWEIGHT/STANDARD/FULL 哪种模式？
- 当前是否在已批准的 gate scope 内？

## Step 3: 角色调度
- 当前 phase 需要哪些角色？
- 这些角色的前置条件是否满足？
- 是否有角色隔离冲突（self-review）？

## Step 4: 治理一致性自检（T-0052）
- 我刚才的决策是否与 enforcement_hub 一致？
- 是否有静默降级的风险（异常被 catch 吞掉）？
- 配置是否正确传递（没有浅层合并丢键）？
- 路径是否可能被 TOCTOU 绕过？

## Task: 执行与交付
基于 Step 1-4 的结论，执行用户请求并推进 Loop 流程。