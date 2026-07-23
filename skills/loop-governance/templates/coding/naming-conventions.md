# 命名约定模板

> **必填表单。** 缺任何必填项 = 打回重做。技术负责人角色必须完整填写。
> 参考标准：**PEP 8**（Naming Conventions）、**Google Python Style Guide**（Naming）、**Airbnb JavaScript Style Guide**（Naming）。

## 1. 通用原则（必填）

- [ ] **自解释**：命名应该清楚地表达意图，不需要注释就能理解
- [ ] **可读性优先**：`user_count` 优于 `uc`，`get_active_users()` 优于 `gau()`
- [ ] **一致性**：同一概念在项目中始终使用相同的命名
- [ ] **避免缩写**：除非是行业公认的缩写（`id`, `url`, `http`, `json`, `api`, `db`, `ui`）
- [ ] **避免歧义**：不用 `data`, `info`, `temp`, `result` 等过于宽泛的名称
- [ ] **避免误导**：`user_list` 不应该是 dict，`is_valid` 不应该返回字符串
- [ ] **长度适中**：2-4 个单词最佳，不超过 5 个单词
- [ ] **使用领域术语**：使用业务领域中的标准术语，而非技术术语

## 2. 各语言命名规则（必填）

### 2.1 Python

| 元素类型 | 命名风格 | 示例 | 说明 |
|---------|---------|------|------|
| 包/模块 | snake_case | `user_service.py`, `auth_middleware.py` | 简短、全小写、可用下划线 |
| 类 | PascalCase | `UserService`, `AuthMiddleware`, `HttpClient` | 名词或名词短语 |
| 异常类 | PascalCase + Error后缀 | `ValidationError`, `AuthError` | 继承自 Exception |
| 函数/方法 | snake_case | `get_user()`, `calculate_total()` | 动词或动词短语 |
| 变量 | snake_case | `user_count`, `is_active` | 名词 |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` | 模块级常量 |
| 私有成员 | _leading_underscore | `_cache`, `_validate_token()` | 非公开API |
| 内部私有 | __double_leading | `__hash_value` | 名称改写（name mangling） |
| 类型变量 | PascalCase | `T`, `UserType`, `K`, `V` | 泛型参数 |
| 布尔变量 | is_/has_/can_/should_ 前缀 | `is_active`, `has_permission`, `can_edit` | 返回 bool |
| 测试函数 | test_ + 描述 | `test_login_with_valid_credentials()` | pytest 发现规则 |

### 2.2 JavaScript / TypeScript

| 元素类型 | 命名风格 | 示例 | 说明 |
|---------|---------|------|------|
| 文件 | kebab-case | `user-service.js`, `auth-middleware.ts` | 小写 + 连字符 |
| 类/接口/类型 | PascalCase | `UserService`, `IAuthProvider` | 类型以名词 |
| 函数/方法 | camelCase | `getUser()`, `calculateTotal()` | 动词开头 |
| 变量 | camelCase | `userCount`, `isActive` | 名词 |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` | 模块级常量 |
| 私有成员 | _camelCase 或 #private | `_cache`, `#validateToken()` | ES2022+ 用 # |
| React 组件 | PascalCase | `UserProfile`, `LoginForm` | 必须大写开头 |
| React Hook | use + PascalCase | `useAuth`, `useDebounce` | 必须以 use 开头 |
| 事件处理函数 | handle + 事件 | `handleClick()`, `handleSubmit()` | 明确事件处理 |
| 布尔变量 | is/has/can/should 前缀 | `isActive`, `hasPermission` | 返回 bool |
| 枚举 | PascalCase (值可大写) | `UserRole.ADMIN`, `Status.ACTIVE` | |

### 2.3 Go

| 元素类型 | 命名风格 | 示例 | 说明 |
|---------|---------|------|------|
| 包 | 全小写，单数 | `user`, `handler`, `auth` | 不用下划线 |
| 导出标识符 | PascalCase | `UserService`, `GetUser()` | 首字母大写=public |
| 非导出标识符 | camelCase | `userService`, `getUser()` | 首字母小写=private |
| 接口 | PascalCase + er后缀 | `Reader`, `Writer`, `Closer` | 单方法接口 |
| 变量 | camelCase | `userCount`, `isActive` | |
| 常量 | PascalCase 或 camelCase | `MaxRetryCount` | 不用全大写下划线 |
| 缩写 | 全大写/全小写 | `HTTPServer`, `userID`, `parseURL` | |
| 错误变量 | err + 描述 | `errNotFound`, `errTimeout` | |
| 布尔变量 | is/has/can 前缀 | `isActive`, `hasItems` | |

## 3. 项目级命名约定（必填）

### 3.1 数据库命名
| 对象 | 命名规则 | 示例 |
|------|---------|------|
| 数据库名 | snake_case, 单数 | `user_service`, `order_management` |
| 表名 | snake_case, 复数 | `users`, `order_items`, `product_categories` |
| 列名 | snake_case, 单数 | `user_id`, `created_at`, `email_address` |
| 主键 | id 或 {table}_id | `id` 或 `user_id` |
| 外键 | {referenced_table}_id | `order_id`, `product_id` |
| 索引 | idx_{table}_{column} | `idx_users_email`, `idx_orders_user_id` |
| 唯一约束 | uq_{table}_{column} | `uq_users_email` |
| 视图 | v_{name} | `v_active_users` |

### 3.2 API 命名
| 元素 | 命名规则 | 示例 |
|------|---------|------|
| 资源路径 | kebab-case, 复数 | `/api/users`, `/api/order-items` |
| 嵌套资源 | 不超过 2 层 | `/api/users/{id}/orders` |
| 查询参数 | snake_case 或 camelCase | `?page_size=20&sort_by=name` |
| 请求体字段 | snake_case 或 camelCase（统一） | `{"user_name": "zhangsan"}` |
| 版本号 | v{n} 前缀 | `/api/v1/users` |

### 3.3 Git 命名
| 元素 | 命名规则 | 示例 |
|------|---------|------|
| 分支名 | 类型/描述 | `feature/user-login`, `bugfix/oauth-timeout`, `release/v2.1.0` |
| 标签 | v{语义版本} | `v2.1.0`, `v2.1.1-rc1` |
| Commit 消息 | type(scope): 描述 | `feat(auth): add login with email`, `fix(api): handle null user` |

## 4. 特定场景命名指南（必填）

### 4.1 集合命名
| 数据类型 | 命名建议 | 好例子 | 坏例子 |
|---------|---------|--------|--------|
| 列表/数组 | 复数形式 或 _list | `users`, `user_list` | `user_arr`, `list` |
| 字典/Map | _map 或 _by_key 形式 | `user_map`, `users_by_id` | `dict`, `obj` |
| 集合(Set) | _set | `unique_ids`, `visited_set` | `set1`, `s` |
| 数量 | 名词 + _count, num_ | `user_count`, `num_errors` | `cnt`, `n` |

### 4.2 函数命名模式
| 行为 | 前缀 | 示例 |
|------|------|------|
| 获取数据 | get_ / fetch_ / find_ | `get_user()`, `find_by_email()` |
| 设置数据 | set_ / update_ | `set_timeout()`, `update_profile()` |
| 创建 | create_ / new_ / build_ | `create_user()`, `build_query()` |
| 删除 | delete_ / remove_ / drop_ | `delete_user()`, `remove_from_cache()` |
| 判断/查询 | is_ / has_ / can_ / check_ | `is_valid()`, `has_permission()`, `check_exists()` |
| 转换 | to_ / from_ / parse_ / format_ | `to_json()`, `parse_config()`, `format_date()` |
| 事件处理 | on_ / handle_ | `on_click()`, `handle_error()` |
| 初始化 | init_ / setup_ / load_ | `init_db()`, `load_config()` |
| 验证 | validate_ / verify_ / ensure_ | `validate_email()`, `ensure_dir_exists()` |

### 4.3 布尔变量命名
| 含义 | 推荐命名 | 避免命名 |
|------|---------|---------|
| 是否存在 | `exists`, `is_present` | `flag`, `check` |
| 是否激活 | `is_active`, `is_enabled` | `status`, `active` |
| 是否可见 | `is_visible`, `is_hidden` | `visible` |
| 是否有效 | `is_valid`, `is_expired` | `valid` |
| 是否为空 | `is_empty`, `is_blank` | `empty` |
| 是否拥有 | `has_*` | `own`, `possess` |
| 是否成功 | `is_successful`, `has_failed` | `success` |
| 是否允许 | `can_*`, `is_allowed` | `allow` |

## 5. 反模式（必读，这些命名禁止出现）

| 反模式 | 问题 | 应改为 |
|--------|------|--------|
| 单字母变量（循环除外） | `x`, `y`, `t` | `user`, `order` |
| 拼音命名 | `yonghu`, `shangpin` | `user`, `product` |
| 无意义缩写 | `usrCnt`, `calcTtl` | `userCount`, `calculateTotal` |
| 匈牙利命名法 | `strName`, `iCount` | `name`, `count` (类型从上下文/类型注解获知) |
| 数字后缀 | `user1`, `user2`, `thing_a` | 找到更具体的名称 |
| 否定式布尔 | `is_not_found`, `disabled` | `is_found`, `is_enabled` (避免双重否定) |
| 过于宽泛的名称 | `data`, `info`, `obj`, `temp` | 找到具体的领域名称 |
| 类型词缀（语言有类型系统时） | `user_string`, `count_int` | `user_name`, `user_count` |

## 6. 填写示例

> 以 Python Web 后端项目为例的命名约定：

| 元素 | 示例值 |
|------|--------|
| 语言 | Python 3.10+ |
| 文件名 | `user_service.py`, `auth_middleware.py` |
| 类名 | `UserService`, `OrderController`, `JwtTokenGenerator` |
| 函数名 | `get_user_by_id()`, `create_order()`, `validate_email()` |
| 变量名 | `user_count`, `is_active`, `order_item` |
| 常量名 | `MAX_PAGE_SIZE`, `DEFAULT_CACHE_TTL` |
| 私有成员 | `_connection_pool`, `_build_sql()` |
| 数据库表 | `users`, `orders`, `order_items` |
| 数据库列 | `user_id`, `created_at`, `updated_by` |
| API路径 | `/api/v1/users`, `/api/v1/orders` |
| Git分支 | `feature/email-verification`, `bugfix/login-timeout` |

## 7. 检查清单（必填，代码评审时逐项检查）

- [ ] 所有命名是否符合对应语言的命名风格
- [ ] 函数/方法名是否以动词开头
- [ ] 布尔变量是否以 is_/has_/can_ 开头
- [ ] 类名是否为名词或名词短语
- [ ] 常量是否全大写
- [ ] 是否避免了拼音命名
- [ ] 是否避免了单字母变量名
- [ ] 是否避免了无意义缩写
- [ ] 模块/文件名是否符合项目约定
- [ ] API 路径是否符合 RESTful 约定
- [ ] 数据库命名是否符合约定
- [ ] Git 分支/提交信息是否符合约定

## 8. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| PEP 8 - Naming Conventions | https://peps.python.org/pep-0008/ | Python 命名规则 |
| Google Python Style Guide - Naming | https://google.github.io/styleguide/pyguide.html | 命名规范、反模式 |
| Airbnb JavaScript Style Guide - Naming | https://javascript.airbnb.tech/#naming-conventions | JS/TS 命名规则 |
| Go Code Review Comments - Naming | https://go.dev/wiki/CodeReviewComments | Go 命名规则 |
