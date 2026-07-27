# 安全检查清单——各扫描项的规则依据

## 依赖 CVE 扫描
| 语言 | 工具 | 命令 | 门槛 |
|---|---|---|---|
| JavaScript/TypeScript | npm audit | `npm audit --json` | 0 HIGH, 0 CRITICAL |
| Python | pip-audit | `pip-audit -r requirements.txt --format json` | 0 HIGH, 0 CRITICAL |

安全工程师应首先检查质量工程师的 audit 结果——如果已通过且有明确timestamp（1小时内），可直接复用。

## 密钥泄露扫描
| 工具 | 命令 | 门槛 |
|---|---|---|
| detect-secrets | `detect-secrets scan --all-files <root>` | 0 命中 |

常见命中模式：AWS Access Key(AKIA...)、GitHub Token(ghp_...)、OpenAI Key(sk-...)、私钥块(-----BEGIN...PRIVATE KEY-----)、password=明文、secret=明文。

## 注入面检测规则
**HIGH 风险（命中=BLOCKED）**：os.system()、subprocess shell=True、eval()、exec()、SQL字符串拼接、dangerouslySetInnerHTML。
**MEDIUM 风险（命中=警告）**：innerHTML赋值、document.write()、|raw模板过滤器。

## 容器镜像扫描
| 工具 | 命令 | 门槛 |
|---|---|---|
| trivy | `trivy image --severity HIGH,CRITICAL --format json <image>` | 0 HIGH, 0 CRITICAL |

## 权限模型审计
检查每个POST/PUT/DELETE路由是否有鉴权中间件(@login_required/authMiddleware/Depends(get_current_user)等)。标记缺少鉴权的端点→BLOCKED。

## 不可接受的豁免理由
"这是测试环境""只有内网能访问""用户量少不会有人攻击""框架已处理""AI不会写不安全代码"——以上理由均不被接受。
