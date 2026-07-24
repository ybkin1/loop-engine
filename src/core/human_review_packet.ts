/**
 * human_review_packet.ts — Human Review Packet Generator
 *
 * Translates technical outputs into decision packages understandable
 * by non-technical stakeholders. Each packet contains "what we did",
 * "key choices", "risks", and "decisions required".
 *
 * Ported from ZCode loop_core/human_review_packet.py.
 */

import { randomUUID } from "node:crypto";

// ---------------------------------------------------------------------------
// Enums & Interfaces
// ---------------------------------------------------------------------------

export enum PacketType {
  GATE_APPROVAL = "GATE_APPROVAL",
  VETO_ESCALATION = "VETO_ESCALATION",
  CHANGE_REQUEST = "CHANGE_REQUEST",
  RISK_ACCEPTANCE = "RISK_ACCEPTANCE",
}

export interface KeyChoice {
  question: string;
  option_a: string;
  option_b: string;
  why_a: string;
  why_not_b: string;
  risk_if_wrong: string;
}

export interface RiskItem {
  risk: string;
  likelihood: "LOW" | "MEDIUM" | "HIGH";
  impact: "LOW" | "MEDIUM" | "HIGH";
  analogy: string;
  mitigation: string;
}

export interface DecisionRequired {
  question: string;
  options: string[];
  recommendation: string;
  deadline?: string;
}

export interface HumanReviewPacket {
  packet_id: string;
  packet_type: PacketType;
  created_at: string;
  what_we_did: string;
  what_changed: string;
  key_choices: KeyChoice[];
  risks: RiskItem[];
  decisions_required: DecisionRequired[];
  phase_id?: string;
  task_id?: string;
}

// ---------------------------------------------------------------------------
// Technical-risk → plain-language mapping (15 entries)
// ---------------------------------------------------------------------------

const TECHNICAL_RISK_MAP: Record<string, string> = {
  "sql injection":
    "坏人可能通过输入框偷走数据库里的信息",
  "xss":
    "恶意脚本可能嵌入网页，在访客的浏览器里偷偷执行",
  "n+1 query":
    "页面可能会很慢，因为每次显示一条数据都要单独查一次数据库",
  "race condition":
    "两个人同时操作同一条数据时，可能会丢失其中一个人的修改",
  "memory leak":
    "程序运行越久占用的内存越多，最终可能导致系统崩溃",
  "deadlock":
    "两个程序互相等待对方释放资源，结果谁都动不了，像两辆车在窄路相遇谁也不让",
  "csrf":
    "攻击者可能诱导用户点击链接，以用户身份执行未授权的操作",
  "hardcoded secrets":
    "密码或密钥写在代码里，任何能看到代码的人都可能获取它们",
  "missing index":
    "数据库查询会越来越慢，就像在一本没有目录的书里逐页翻找",
  "circular dependency":
    "模块之间互相依赖形成死循环，改一个地方可能导致其他地方出问题",
  "unvalidated input":
    "用户输入的数据没有经过检查，可能导致程序出错或安全漏洞",
  "insufficient logging":
    "出了问题时没有足够的记录来排查原因，就像没有监控摄像头的商店被盗后无法追查",
  "single point of failure":
    "某个关键组件一旦故障，整个系统都会瘫痪，如同只有一条路通往的城市",
  "version skew":
    "不同组件使用不同版本的接口，可能导致数据格式不兼容而报错",
  "timeout misconfiguration":
    "等待响应的时间设置不当，可能导致请求过早失败或让用户等太久",
};

// ---------------------------------------------------------------------------
// PacketBuilder
// ---------------------------------------------------------------------------

export class PacketBuilder {
  /**
   * Build a gate approval packet from phase completion data.
   */
  static fromPhaseCompletion(params: {
    phase: string;
    taskId: string;
    artifacts: string[];
    qualityReport?: { test: string; lint: string; build: string };
    reviewResults?: Record<string, string>;
  }): HumanReviewPacket {
    const { phase, taskId, artifacts, qualityReport, reviewResults } = params;

    // -- what_we_did --------------------------------------------------------
    const what_we_did = `完成了 ${phase} 阶段的所有任务`;

    // -- what_changed -------------------------------------------------------
    const what_changed =
      artifacts.length > 0
        ? `产出了以下交付物：\n${artifacts.map((a) => `- ${a}`).join("\n")}`
        : "本阶段未产出额外交付物";

    // -- key_choices --------------------------------------------------------
    const key_choices: KeyChoice[] = [];

    if (qualityReport) {
      const allPassed =
        qualityReport.test === "pass" &&
        qualityReport.lint === "pass" &&
        qualityReport.build === "pass";

      key_choices.push({
        question: "质量报告结果如何？",
        option_a: allPassed
          ? "所有检查（测试、代码规范、构建）均已通过"
          : "部分检查通过，但存在需要关注的问题",
        option_b: allPassed
          ? "无需额外关注，质量达标"
          : "暂停推进，先修复未通过的项目",
        why_a: allPassed
          ? "质量指标全部达标，可以安全地进入下一阶段"
          : "通过的项目表明整体方向正确，但遗留问题可能影响后续工作",
        why_not_b: allPassed
          ? "当前阶段质量已验证，不需要额外审查"
          : "带着问题进入下一阶段会增加返工成本和风险",
        risk_if_wrong: allPassed
          ? "如果误判为通过而实际存在问题，可能在后期引入难以修复的缺陷"
          : "如果过度谨慎地暂停，可能延误项目进度",
      });
    }

    // -- risks --------------------------------------------------------------
    const risks: RiskItem[] = [];

    if (reviewResults) {
      for (const [area, result] of Object.entries(reviewResults)) {
        if (result !== "approved" && result !== "pass") {
          risks.push({
            risk: `${area} 评审未通过（状态: ${result}）`,
            likelihood: "MEDIUM",
            impact: "HIGH",
            analogy: `就像盖房子时${area}部分没通过验收，如果不修正就继续往上盖，迟早会出问题`,
            mitigation: `在进入下一阶段前解决 ${area} 的评审意见`,
          });
        }
      }
    }

    if (qualityReport) {
      if (qualityReport.test !== "pass") {
        risks.push({
          risk: "测试未全部通过",
          likelihood: "HIGH",
          impact: "HIGH",
          analogy: "就像新车出厂前刹车测试没过关——不能带着已知缺陷上路",
          mitigation: "修复失败的测试用例后再推进",
        });
      }
      if (qualityReport.build !== "pass") {
        risks.push({
          risk: "构建未通过",
          likelihood: "HIGH",
          impact: "HIGH",
          analogy: "就像拼图少了一块拼不上——整个产品无法组装完成",
          mitigation: "排查构建错误并修复",
        });
      }
    }

    // -- decisions_required -------------------------------------------------
    const decisions_required: DecisionRequired[] = [
      {
        question: "是否批准进入下一阶段？",
        options: ["批准", "驳回", "有条件批准（需完成指定修正项）"],
        recommendation:
          risks.length === 0
            ? "所有检查通过，建议批准进入下一阶段"
            : `存在 ${risks.length} 项风险，建议先解决后再批准`,
      },
    ];

    return {
      packet_id: randomUUID(),
      packet_type: PacketType.GATE_APPROVAL,
      created_at: new Date().toISOString(),
      what_we_did,
      what_changed,
      key_choices,
      risks,
      decisions_required,
      phase_id: phase,
      task_id: taskId,
    };
  }

  /**
   * Build a veto escalation packet.
   */
  static fromVetoEscalation(params: {
    vetos: Array<{ role_id: string; reason: string; severity: string }>;
    taskId: string;
  }): HumanReviewPacket {
    const { vetos, taskId } = params;

    const what_we_did = `发现了 ${vetos.length} 个角色间的分歧`;

    const what_changed = vetos
      .map((v) => `- ${v.role_id} 提出了否决: ${v.reason}（严重程度: ${v.severity}）`)
      .join("\n");

    const key_choices: KeyChoice[] = vetos.map((v) => ({
      question: `${v.role_id} 否决了当前方案，如何处理？`,
      option_a: "采纳否决意见，修改方案",
      option_b: "维持当前方案，覆盖否决",
      why_a: `否决理由: ${v.reason}。采纳可以避免后续因此产生的风险`,
      why_not_b: "维持方案可能加快进度，但忽略了该角色提出的隐患",
      risk_if_wrong:
        v.severity === "high"
          ? "这是一个高严重程度的否决，忽视它可能导致严重后果"
          : "忽视此否决可能在中后期引发返工",
    }));

    const risks: RiskItem[] = [
      {
        risk: "角色间的分歧未得到解决",
        likelihood: "HIGH",
        impact: "HIGH",
        analogy: "就像几个建筑师对地基设计意见不一，如果不协调好就开工，楼可能盖到一半发现结构不对",
        mitigation: "召集相关角色开会讨论，达成共识后再推进",
      },
    ];

    if (vetos.some((v) => v.severity === "high")) {
      risks.push({
        risk: "存在高严重程度的否决",
        likelihood: "HIGH",
        impact: "HIGH",
        analogy: "如同安全检测发现了重大隐患——不处理就继续，后果可能非常严重",
        mitigation: "优先处理高严重程度的否决项",
      });
    }

    const decisions_required: DecisionRequired[] = [
      {
        question: "如何解决这些分歧？",
        options: [
          "全部采纳否决意见",
          "逐一评估每个否决",
          "召集评审会议讨论",
          "由项目负责人裁定",
        ],
        recommendation:
          vetos.some((v) => v.severity === "high")
            ? "建议优先处理高严重程度否决，再逐一评估其余项"
            : "建议逐一评估每个否决意见",
      },
    ];

    return {
      packet_id: randomUUID(),
      packet_type: PacketType.VETO_ESCALATION,
      created_at: new Date().toISOString(),
      what_we_did,
      what_changed,
      key_choices,
      risks,
      decisions_required,
      task_id: taskId,
    };
  }

  /**
   * Build a change request packet.
   */
  static fromChangeRequest(params: {
    description: string;
    impact: string;
    affectedModules: string[];
  }): HumanReviewPacket {
    const { description, impact, affectedModules } = params;

    const what_we_did = "收到了一个变更请求";

    const what_changed = [
      `变更描述: ${description}`,
      `预期影响: ${impact}`,
      "",
      "受影响的模块:",
      ...affectedModules.map((m) => `- ${m}`),
    ].join("\n");

    const key_choices: KeyChoice[] = [
      {
        question: "是否接受这个变更请求？",
        option_a: "接受变更，立即纳入当前迭代",
        option_b: "推迟变更，记录到后续迭代",
        why_a: "及时响应需求变化可以确保产品更符合预期",
        why_not_b: "推迟可以避免打乱当前迭代节奏，但可能延迟需求交付",
        risk_if_wrong:
          "如果接受但不该接受，可能导致当前迭代范围蔓延；如果推迟但不该推迟，可能导致交付物不符合需求",
      },
    ];

    const risks: RiskItem[] = [
      {
        risk: `变更影响 ${affectedModules.length} 个模块`,
        likelihood: affectedModules.length > 3 ? "HIGH" : "MEDIUM",
        impact: "MEDIUM",
        analogy: `就像修改一栋楼的${affectedModules.length}个房间的设计——改动越多，越可能影响到其他部分`,
        mitigation: "逐个评估受影响模块的改动范围，确保不会引发连锁反应",
      },
      {
        risk: "变更可能导致进度延迟",
        likelihood: "MEDIUM",
        impact: "MEDIUM",
        analogy: "如同已经出发的火车要临时改道——需要额外时间重新规划路线",
        mitigation: "评估变更所需额外工时，调整排期",
      },
    ];

    const decisions_required: DecisionRequired[] = [
      {
        question: "如何处理这个变更请求？",
        options: [
          "立即接受并纳入当前迭代",
          "接受但推迟到下一迭代",
          "拒绝，维持当前范围",
          "需要更多信息后再决定",
        ],
        recommendation:
          affectedModules.length > 3
            ? "影响范围较大，建议详细评估后再决定"
            : "影响范围可控，建议纳入当前迭代",
      },
    ];

    return {
      packet_id: randomUUID(),
      packet_type: PacketType.CHANGE_REQUEST,
      created_at: new Date().toISOString(),
      what_we_did,
      what_changed,
      key_choices,
      risks,
      decisions_required,
    };
  }

  /**
   * Translate technical risk to plain language.
   *
   * Uses a built-in mapping of 15 common technical risks.
   * Falls back to a generic translation if no exact match is found.
   */
  static translateTechnicalRisk(technicalDescription: string): string {
    const lower = technicalDescription.toLowerCase();

    // Try exact match first
    for (const [key, translation] of Object.entries(TECHNICAL_RISK_MAP)) {
      if (lower === key) {
        return translation;
      }
    }

    // Try partial match
    for (const [key, translation] of Object.entries(TECHNICAL_RISK_MAP)) {
      if (lower.includes(key)) {
        return translation;
      }
    }

    // Fallback: wrap original with a note
    return `[技术术语] ${technicalDescription} — 建议请技术人员用通俗语言解释此风险`;
  }
}

// ---------------------------------------------------------------------------
// Output formatters
// ---------------------------------------------------------------------------

/** Convert packet to Markdown format */
export function toMarkdown(packet: HumanReviewPacket): string {
  const lines: string[] = [];

  lines.push(`# 评审包: ${packet.packet_type}`);
  lines.push("");
  lines.push(`> 包ID: ${packet.packet_id}  `);
  lines.push(`> 创建时间: ${packet.created_at}`);
  if (packet.phase_id) lines.push(`> 阶段: ${packet.phase_id}`);
  if (packet.task_id) lines.push(`> 任务: ${packet.task_id}`);
  lines.push("");

  // 做了什么
  lines.push("## 做了什么");
  lines.push(packet.what_we_did);
  lines.push("");

  // 发生了什么变化
  lines.push("## 发生了什么变化");
  lines.push(packet.what_changed);
  lines.push("");

  // 关键选择
  if (packet.key_choices.length > 0) {
    lines.push("## 关键选择");
    packet.key_choices.forEach((choice, i) => {
      lines.push(`${i + 1}. **${choice.question}**`);
      lines.push(`   - 方案A: ${choice.option_a} — ${choice.why_a}`);
      lines.push(`   - 方案B: ${choice.option_b} — ${choice.why_not_b}`);
      lines.push(`   - 如果选错的风险: ${choice.risk_if_wrong}`);
      lines.push("");
    });
  }

  // 风险
  if (packet.risks.length > 0) {
    lines.push("## 风险");
    lines.push("| 风险 | 可能性 | 影响 | 类比 | 缓解措施 |");
    lines.push("|------|--------|------|------|----------|");
    for (const r of packet.risks) {
      lines.push(`| ${r.risk} | ${r.likelihood} | ${r.impact} | ${r.analogy} | ${r.mitigation} |`);
    }
    lines.push("");
  }

  // 需要你决定
  if (packet.decisions_required.length > 0) {
    lines.push("## 需要你决定");
    for (const d of packet.decisions_required) {
      lines.push(`- **${d.question}**`);
      lines.push(`  选项: ${d.options.join(", ")}`);
      lines.push(`  建议: ${d.recommendation}`);
      if (d.deadline) {
        lines.push(`  截止时间: ${d.deadline}`);
      }
      lines.push("");
    }
  }

  return lines.join("\n");
}

/** Convert packet to plain text format */
export function toPlainText(packet: HumanReviewPacket): string {
  const lines: string[] = [];
  const separator = "=".repeat(60);

  lines.push(separator);
  lines.push(`评审包: ${packet.packet_type}`);
  lines.push(separator);
  lines.push(`包ID:     ${packet.packet_id}`);
  lines.push(`创建时间: ${packet.created_at}`);
  if (packet.phase_id) lines.push(`阶段:     ${packet.phase_id}`);
  if (packet.task_id) lines.push(`任务:     ${packet.task_id}`);
  lines.push("");

  lines.push("--- 做了什么 ---");
  lines.push(packet.what_we_did);
  lines.push("");

  lines.push("--- 发生了什么变化 ---");
  lines.push(packet.what_changed);
  lines.push("");

  if (packet.key_choices.length > 0) {
    lines.push("--- 关键选择 ---");
    packet.key_choices.forEach((choice, i) => {
      lines.push(`${i + 1}. ${choice.question}`);
      lines.push(`   方案A: ${choice.option_a}`);
      lines.push(`     原因: ${choice.why_a}`);
      lines.push(`   方案B: ${choice.option_b}`);
      lines.push(`     原因: ${choice.why_not_b}`);
      lines.push(`   选错风险: ${choice.risk_if_wrong}`);
      lines.push("");
    });
  }

  if (packet.risks.length > 0) {
    lines.push("--- 风险 ---");
    for (const r of packet.risks) {
      lines.push(`* ${r.risk}`);
      lines.push(`  可能性: ${r.likelihood}  |  影响: ${r.impact}`);
      lines.push(`  类比: ${r.analogy}`);
      lines.push(`  缓解: ${r.mitigation}`);
      lines.push("");
    }
  }

  if (packet.decisions_required.length > 0) {
    lines.push("--- 需要你决定 ---");
    for (const d of packet.decisions_required) {
      lines.push(`* ${d.question}`);
      lines.push(`  选项: ${d.options.join(", ")}`);
      lines.push(`  建议: ${d.recommendation}`);
      if (d.deadline) {
        lines.push(`  截止时间: ${d.deadline}`);
      }
      lines.push("");
    }
  }

  lines.push(separator);
  return lines.join("\n");
}
