# 发布检查清单——上线前的强制检查项

## 1. 构建可重复性
标准：同一commit两次构建产出相同SHA256。
验证：`docker build --no-cache -t app:sha-test-1 . && docker save | sha256sum` 执行两次对比。
不可接受："基本一样就差元数据""开发环境构建不出来""CI每次都一样"(需本地验证)。
通过：lockfile存在+Dockerfile无latest tag+SHA256一致。

## 2. 部署自动化
标准：部署全程由CI/CD pipeline或IaC定义，无人工ssh操作。
验证：搜索CI/CD配置文件，逐行确认无`ssh user@server`命令。
不可接受："运维知道怎么部署""有文档照做就行""生产环境只能手动"。
通过：完整CI/CD pipeline+无ssh命令+可自动触发。

## 3. 健康检查
标准：至少一个健康检查端点。推荐/health(进程存活)、/ready(依赖就绪)、/live(K8s liveness)。
验证：`grep -rn '/health\|/ready\|/live' src/`；如服务运行则curl测试。
不可接受："应用太小不需要""nginx层有""应用不会挂"。
通过：至少一个健康检查路由定义+响应格式可解析。

## 4. 结构化日志
标准：JSON输出，每条含timestamp(ISO 8601)、level、message、trace_id、logger。
验证：grep搜索structlog/winston/zerolog/logrus配置。
不可接受："有print""去了ELK再做结构化""printf也挺好"。
通过：源代码中有结构化日志库配置且至少含timestamp+level+message。

## 5. 回滚方案
标准：触发条件+执行步骤(≤3步)+验证方法+通知对象。预估时间≤5分钟。
不可接受："出问题再说""数据库有备份""应该能30分钟内"。
通过：回滚文档或CI/CD job存在+步骤≤3+预估≤5分钟。

## 6. 监控告警
标准：CPU>80%/内存>85%/5xx错误率>1%/P95延迟>目标值——四项均有告警规则。通知渠道≥邮件+IM。
不可接受："看Grafana仪表盘就行""之前没告警也跑了两年""用户会报的"。

## 7. 配置管理
标准：所有环境配置通过环境变量或配置服务注入，无硬编码URL/端口/DB连接串。
验证：grep搜索localhost/127.0.0.1/连接字符串。
通过：无硬编码+.env.example存在且变量齐全。

## 8. 密钥管理
标准：密钥不通过配置文件或代码传递。来源必须是环境变量（由密钥服务注入）或密钥管理服务API。
验证：复用安全工程师secret_leak结果。不可接受：".env不提交所以安全""只在开发环境用""定期轮换就行"。
通过：安全工程师secret_leak=PASS或自行grep无命中+有密钥管理服务配置。

## 发布绿/红判定
| 条件 | 状态 |
|---|---|
| 8项全通过+上游质量PASS+上游安全PASS | 上线就绪 |
| 任一未通过或上游BLOCKED | 不准上线 |
