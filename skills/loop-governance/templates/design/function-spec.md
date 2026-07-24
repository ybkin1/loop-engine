# 函数/方法规格模板

> **必填表单。** 缺任何必填项 = 打回重做。开发者角色必须完整填写。
> 参考标准：**Google Python Style Guide**（函数定义）、**PEP 8**（文档字符串）、**Instructor 结构化输出**。

## 1. 函数标识（必填）

| 字段 | 内容 |
|------|------|
| 函数名 | [如：calculate_order_total] |
| 所属模块/文件 | [如：orders/calculator.py] |
| 所属类（如适用） | [如：OrderCalculator] |
| 可见性 | [public / private / protected] |
| 作者 | [姓名/角色] |
| 版本 | v1.0 |
| 创建日期 | YYYY-MM-DD |

## 2. 函数签名（必填）

```python
def calculate_order_total(
    items: List[OrderItem],
    discount_code: Optional[str] = None,
    tax_rate: float = 0.0
) -> OrderTotal:
    """
    [一句话描述函数功能]

    [详细说明，包括算法、边界条件、异常行为]
    """
```

## 3. 规格定义（必填）

### 3.1 前置条件（Preconditions）
- [ ] 调用前必须满足的条件1：[如：items 列表不为空]
- [ ] 调用前必须满足的条件2：[如：tax_rate >= 0]
- [ ] 调用前必须满足的条件3：[如：调用方已获取数据库连接]

### 3.2 后置条件（Postconditions）
- [ ] 调用后保证的条件1：[如：返回值 total >= 0]
- [ ] 调用后保证的条件2：[如：输入 items 未被修改]
- [ ] 调用后保证的条件3：[如：折扣码若有效则被标记为"已使用"]

### 3.3 不变量（Invariants）
- [ ] 执行过程中始终成立的条件1：[如：running_total >= 0]
- [ ] 执行过程中始终成立的条件2：[如：len(items) 不变]

## 4. 参数详细说明（必填）

| 参数名 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|--------|------|------|
| items | List[OrderItem] | 是 | - | len >= 1 | 订单中的商品列表 |
| discount_code | Optional[str] | 否 | None | 长度 4-20, 大写字母+数字 | 优惠券代码 |
| tax_rate | float | 否 | 0.0 | 0.0 <= rate <= 1.0 | 税率，例如 0.13 表示 13% |

**填写示例：**
| 参数名 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|--------|------|------|
| items | List[OrderItem] | 是 | - | len >= 1, len <= 100 | 订单商品，每个item含price和quantity |
| discount_code | Optional[str] | 否 | None | regex: ^[A-Z0-9]{4,20}$ | 如 "SAVE20" |
| tax_rate | float | 否 | 0.0 | 0.0 <= x <= 1.0 | 如 0.13 = 13%增值税 |

## 5. 返回值说明（必填）

| 字段 | 类型 | 是否恒有值 | 说明 |
|------|------|----------|------|
| subtotal | Decimal | 是 | 商品总价（未折扣） |
| discount_amount | Decimal | 是 | 折扣金额（无折扣时为 0） |
| taxable_amount | Decimal | 是 | 应税金额 |
| tax_amount | Decimal | 是 | 税额 |
| total | Decimal | 是 | 最终应付金额 = subtotal - discount + tax |
| applied_discount_code | Optional[str] | 否 | 实际应用的折扣码，无折扣时为 None |

## 6. 异常定义（必填）

| 异常类型 | 触发条件 | 错误码 | 调用方应如何处理 |
|---------|---------|--------|---------------|
| ValueError | items 为空列表 | INVALID_ITEMS | 提示用户添加商品 |
| ValueError | tax_rate 超出 [0, 1] | INVALID_TAX_RATE | 使用默认税率重试 |
| DiscountExpiredError | 折扣码已过期 | DISCOUNT_EXPIRED | 提示用户折扣码已失效 |
| DiscountExhaustedError | 折扣码已用完 | DISCOUNT_EXHAUSTED | 提示用户折扣码已被领完 |

## 7. 边界条件（必填）

| 边界条件 | 期望行为 | 示例 |
|---------|---------|------|
| 空输入 | [如：抛出 ValueError] | items=[], → ValueError |
| 单元素输入 | [如：正常计算] | items=[{price:10, qty:1}], tax_rate=0 → total=10 |
| 最大输入 | [如：100个商品正常计算] | items=100个, → 正常 |
| 零值 | [如：total=0 正常返回] | items=[{price:0, qty:1}] → total=0 |
| 负值 | [如：抛出 ValueError] | price=-10 → ValueError |

## 8. 性能特征

| 指标 | 目标 | 说明 |
|------|------|------|
| 时间复杂度 | [如：O(n), n=len(items)] | [算法说明] |
| 空间复杂度 | [如：O(1)] | [说明] |
| 预期输入规模 | [如：1-100 items] | [典型场景] |
| 是否需要缓存 | [是/否] | [缓存策略] |

## 9. 副作用（必填，无则填"无"）

| 副作用类型 | 描述 | 是否可逆 |
|-----------|------|---------|
| [如：数据库写入] | [写入订单记录到 orders 表] | 否（但可冲正） |
| [如：日志] | [INFO级别记录计算明细] | 是（日志可清理） |
| [如：缓存更新] | [刷新用户购物车缓存] | 否 |

## 10. 使用示例（必填，至少 1 个）

```python
# 示例 1：正常计算（含折扣和税率）
items = [
    OrderItem(name="Python编程书", price=Decimal("59.00"), quantity=2),
    OrderItem(name="机械键盘", price=Decimal("399.00"), quantity=1),
]
result = calculate_order_total(
    items=items,
    discount_code="SAVE20",
    tax_rate=0.13
)
print(result.total)  # → Decimal("524.32")
# 计算过程: subtotal=517, discount=103.4(=517*0.2), taxable=413.6, tax=53.77, total=467.37

# 示例 2：无折扣
result = calculate_order_total(items=items, tax_rate=0.0)
print(result.total)  # → Decimal("517.00")

# 示例 3：错误处理
try:
    calculate_order_total(items=[], tax_rate=0.13)
except ValueError as e:
    print(f"错误: {e}")  # → 错误: 订单商品列表不能为空
```

## 11. 测试要点

| 测试场景 | 输入 | 期望输出 |
|---------|------|---------|
| 正常流程-有折扣 | items=[...], discount="SAVE20", tax=0.13 | total=467.37 |
| 正常流程-无折扣 | items=[...], tax=0 | total=517.00 |
| 异常-空items | items=[], ... | ValueError("订单商品列表不能为空") |
| 异常-税率越界 | items=[...], tax=1.5 | ValueError("税率必须在 0 到 1 之间") |
| 边界-单价为0 | items=[{price:0, qty:5}], tax=0 | total=0 |

## 12. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| Google Python Style Guide - Functions | https://google.github.io/styleguide/pyguide.html | 函数定义、参数类型、文档字符串 |
| PEP 8 - Docstring | https://peps.python.org/pep-0008/ | 文档字符串格式 |
| Instructor 结构化输出 | https://python.useinstructor.com/ | 字段级约束、验证规则 |
