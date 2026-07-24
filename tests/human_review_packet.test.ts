import { describe, it, expect } from 'vitest';
import { PacketBuilder, PacketType, toMarkdown, toPlainText } from '../src/core/human_review_packet.js';

describe('PacketType enum', () => {
  it('contains GATE_APPROVAL/VETO_ESCALATION/CHANGE_REQUEST/RISK_ACCEPTANCE', () => {
    expect(PacketType.GATE_APPROVAL).toBe('GATE_APPROVAL');
    expect(PacketType.VETO_ESCALATION).toBe('VETO_ESCALATION');
    expect(PacketType.CHANGE_REQUEST).toBe('CHANGE_REQUEST');
    expect(PacketType.RISK_ACCEPTANCE).toBe('RISK_ACCEPTANCE');
  });
});

describe('PacketBuilder.fromPhaseCompletion', () => {
  it('生成正确的 packet_type', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: ['docs/requirements.md'],
    });
    expect(packet.packet_type).toBe(PacketType.GATE_APPROVAL);
  });

  it('what_we_did 包含 phase 名称', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    expect(packet.what_we_did).toContain('requirements');
  });

  it('decisions_required 非空', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    expect(packet.decisions_required.length).toBeGreaterThan(0);
  });
});

describe('PacketBuilder.fromVetoEscalation', () => {
  it('生成 VETO_ESCALATION 类型', () => {
    const packet = PacketBuilder.fromVetoEscalation({
      vetos: [{ role_id: 'R06', reason: 'test', severity: 'high' }],
      taskId: 'task-1',
    });
    expect(packet.packet_type).toBe(PacketType.VETO_ESCALATION);
  });

  it('key_choices 数量匹配 vetos', () => {
    const vetos = [
      { role_id: 'R06', reason: 'test1', severity: 'high' },
      { role_id: 'R09', reason: 'test2', severity: 'medium' },
    ];
    const packet = PacketBuilder.fromVetoEscalation({ vetos, taskId: 'task-1' });
    expect(packet.key_choices.length).toBe(vetos.length);
  });
});

describe('PacketBuilder.fromChangeRequest', () => {
  it('生成 CHANGE_REQUEST 类型', () => {
    const packet = PacketBuilder.fromChangeRequest({
      description: 'test change',
      impact: 'low',
      affectedModules: ['module1'],
    });
    expect(packet.packet_type).toBe(PacketType.CHANGE_REQUEST);
  });
});

describe('PacketBuilder.translateTechnicalRisk', () => {
  it('"SQL injection" → 包含通俗描述', () => {
    const translation = PacketBuilder.translateTechnicalRisk('SQL injection');
    expect(translation).toContain('坏人');
  });

  it('未知风险 → 返回原始描述', () => {
    const unknownRisk = 'some unknown technical risk';
    const translation = PacketBuilder.translateTechnicalRisk(unknownRisk);
    expect(translation).toContain(unknownRisk);
  });
});

describe('toMarkdown', () => {
  it('输出包含 "# 评审包" 标题', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    const md = toMarkdown(packet);
    expect(md).toContain('# 评审包');
  });

  it('输出包含 "## 做了什么"', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    const md = toMarkdown(packet);
    expect(md).toContain('## 做了什么');
  });

  it('输出包含 "## 风险"', () => {
    const packet = PacketBuilder.fromVetoEscalation({
      vetos: [{ role_id: 'R06', reason: 'test', severity: 'high' }],
      taskId: 'task-1',
    });
    const md = toMarkdown(packet);
    expect(md).toContain('## 风险');
  });

  it('packet_id 出现在输出中', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    const md = toMarkdown(packet);
    expect(md).toContain(packet.packet_id);
  });
});

describe('toPlainText', () => {
  it('输出不包含 Markdown 语法 (#)', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    const plainText = toPlainText(packet);
    expect(plainText).not.toContain('#');
  });

  it('packet_id 出现在输出中', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: [],
    });
    const plainText = toPlainText(packet);
    expect(plainText).toContain(packet.packet_id);
  });
});
