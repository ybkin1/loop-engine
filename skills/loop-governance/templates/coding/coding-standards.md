# 编码规范模板

> **必填表单。** 缺任何必填项 = 打回重做。技术负责人角色必须完整填写。
> 参考标准：**PEP 8**、**Google Python Style Guide**、**Airbnb JavaScript Style Guide**。

## 1. 项目基本信息

| 字段 | 内容 |
|------|------|
| 项目名称 | [项目名] |
| 主要语言 | [Python / JavaScript / TypeScript / Go / ...] |
| 版本 | v1.0 |
| 负责人 | [技术负责人] |
| 生效日期 | YYYY-MM-DD |

## 2. 代码格式化（必填）

| 规则项 | 规范 | 工具 | 是否强制执行 |
|--------|------|------|------------|
| 行长度上限 | [如：88 字符（Python）/ 100 字符（JS）] | [ruff / prettier] | [是] |
| 缩进 | [如：4 空格 / 2 空格] | [ruff / prettier] | [是] |
| 缩进风格 | [空格 / Tab] | [编辑器配置] | [是] |
| 行尾空格 | [禁止] | [ruff / prettier] | [是] |
| 文件末尾空行 | [1 个空行] | [ruff / prettier] | [是] |
| 引号风格 | [双引号 / 单引号] | [ruff / prettier] | [是] |
| 分号 | [禁止 / 必须] | [prettier] | [是] |
| 导入排序 | [标准库 → 第三方 → 本地 字母序] | [ruff isort / eslint] | [是] |

**参考配置示例：**
```toml
# ruff.toml (Python)
line-length = 88
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

## 3. 命名规范（必填）

### 3.1 通用规则
- [ ] 命名必须自解释（见名知意），避免单字母变量（循环变量除外）
- [ ] 避免缩写，除非是行业通用缩写（如 `id`, `url`, `http`）
- [ ] 布尔变量以 `is_` / `has_` / `can_` 开头
- [ ] 不使用拼音命名

### 3.2 各元素命名规则
| 元素 | Python 规范 | JavaScript/TypeScript 规范 | 示例 |
|------|------------|--------------------------|------|
| 模块/文件名 | snake_case | kebab-case | user_service.py / user-service.js |
| 类名 | PascalCase | PascalCase | UserService, OrderController |
| 函数/方法 | snake_case | camelCase | get_user_by_id() / getUserById() |
| 变量 | snake_case | camelCase | user_count / userCount |
| 常量 | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | MAX_RETRY_COUNT |
| 私有成员 | _leading_underscore | _leadingUnderscore 或 #private | _internal_cache |
| 接口/类型 | PascalCase | PascalCase (+ I前缀可选) | UserRepository / IUserRepository |

## 4. 代码结构规范（必填）

### 4.1 文件结构
```python
# Python 文件结构顺序
1. Shebang 行（如需要）: #!/usr/bin/env python3
2. 文件级 docstring: """模块用途。"""
3. __all__ 定义（如需要）
4. 标准库 import
5. 第三方库 import
6. 本地/项目 import
7. 模块级常量和变量
8. 类和函数定义
```

### 4.2 函数规范
- [ ] 单个函数不超过 50 行（复杂逻辑除外，需注释说明）
- [ ] 参数个数不超过 5 个（超过时考虑封装为对象/dict）
- [ ] 嵌套深度不超过 3 层
- [ ] 每个函数只做一件事（单一职责）
- [ ] 避免使用可变默认参数（Python 特有问题）
- [ ] 优先使用早返回（early return）减少嵌套

### 4.3 类规范
- [ ] 单个类不超过 300 行
- [ ] 公开方法数不超过 10 个
- [ ] 优先使用组合而非继承
- [ ] 继承深度不超过 2 层

## 5. 注释规范（必填）

| 注释类型 | 规范 | 示例 |
|---------|------|------|
| 文件级注释 | 必须，说明模块用途 | `"""用户认证相关的服务层函数。"""` |
| 公开函数/方法 | 必须，按 Google Style docstring | 包含 Args/Returns/Raises |
| 私有函数 | 建议，复杂逻辑必须 | 至少一行说明 |
| 类注释 | 必须 | `"""表示一个用户账户实体。"""` |
| 行内注释 | 解释"为什么"而非"是什么" | `# 使用二分查找的原因是数据已排序` |
| TODO 注释 | 格式：`# TODO(owner): description` | `# TODO(zhangsan): 优化为O(log n)` |

## 6. 最佳实践（必填）

### 6.1 通用实践
- [ ] 使用类型注解（Python 3.10+ / TypeScript strict）
- [ ] 异常处理：捕获具体异常，不使用 bare except / catch(Exception)
- [ ] 资源管理：使用上下文管理器（Python `with`）/ try-with-resources（Java）/ RAII
- [ ] 不可变优先：优先使用不可变数据结构
- [ ] 纯函数优先：无副作用的函数优先
- [ ] 避免魔法数字：定义为命名常量
- [ ] 使用 f-string（Python）/ template literals（JS）替代字符串拼接
- [ ] 字典/对象取值用 .get() 或可选链（?.）避免 KeyError/TypeError

### 6.2 Python 特定实践
- [ ] 使用 `dataclass` / `Pydantic BaseModel` 定义数据对象
- [ ] 使用 `pathlib.Path` 而非 `os.path`
- [ ] 使用 `enumerate()` 而非 `range(len())`
- [ ] 使用列表推导式（简单场景，不超过两层）
- [ ] 使用 `logging` 而非 `print()` 输出日志
- [ ] 遵循 "Explicit is better than implicit"（显式优于隐式）

### 6.3 JavaScript/TypeScript 特定实践
- [ ] 使用 `const` 和 `let`，禁用 `var`
- [ ] 使用 `===` 而非 `==`
- [ ] 使用可选链 `?.` 和空值合并 `??`
- [ ] 使用 `async/await` 而非回调
- [ ] 使用解构赋值
- [ ] 使用箭头函数（合适的场景）

## 7. 工具集成（必填）

| 工具类型 | 推荐工具 | 配置文件 | CI 集成 |
|---------|---------|---------|---------|
| Linter | [ruff (Python) / ESLint (JS)] | [ruff.toml / .eslintrc.json] | [是] |
| Formatter | [ruff format / prettier] | [同上] | [是] |
| 类型检查 | [mypy (Python) / tsc (TS)] | [mypy.ini / tsconfig.json] | [是] |
| 安全检查 | [bandit (Python) / npm audit] | [bandit.yaml / .nsprc] | [是] |
| Pre-commit | [pre-commit] | [.pre-commit-config.yaml] | [是] |

## 8. 填写示例

> 以 Python 后端项目为例：

| 规则项 | 示例值 |
|--------|--------|
| 语言 | Python 3.10+ |
| 行长度 | 88 字符 |
| 缩进 | 4 空格 |
| 引号 | 双引号 |
| 命名 | snake_case (变量/函数), PascalCase (类), UPPER_CASE (常量) |
| 类型注解 | 必须，mypy strict mode |
| 函数长度 | ≤ 50 行 |
| 类长度 | ≤ 300 行 |
| 注释 | Google Style docstring (必填公开接口) |
| 格式化工具 | ruff (line-length=88) |
| Lint | ruff (select E,F,I,N,W,UP) |
| 类型检查 | mypy (strict=True) |

## 9. 禁止事项（必填）

| 编号 | 禁止行为 | 原因 | 替代方案 |
|------|---------|------|---------|
| FO-001 | 使用 `print()` 输出日志 | 无级别/无格式/无持久化 | 使用 `logging` 模块 |
| FO-002 | 使用 `except:` (bare except) | 拦截 SystemExit/KeyboardInterrupt | 捕获具体异常类型 |
| FO-003 | 在函数参数中使用可变默认值 `def f(x=[])` | Python 只初始化一次，导致状态共享 | 使用 `def f(x=None): x = x or []` |
| FO-004 | 直接 `import *` | 命名空间污染 | 显式导入或用 `__all__` 控制 |
| FO-005 | 硬编码密钥/密码/Token 在代码中 | 安全风险 | 使用环境变量或密钥管理服务 |

## 10. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| PEP 8 | https://peps.python.org/pep-0008/ | 代码布局、命名约定、编程建议 |
| Google Python Style Guide | https://google.github.io/styleguide/pyguide.html | 语言规则、风格规则 |
| Airbnb JavaScript Style Guide | https://javascript.airbnb.tech/ | JS/TS 编码规范 |
| ruff 配置参考 | https://docs.astral.sh/ruff/configuration/ | 工具集成配置 |
| mypy 配置参考 | https://mypy.readthedocs.io/en/stable/config_file.html | 类型检查配置 |
