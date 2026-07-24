import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { ContextLoader, LoadLevel } from '../src/core/context_loader.js';

// ── LoadLevel enum ──────────────────────────────────────────────

describe('LoadLevel', () => {
  it('包含 MINIMAL/STANDARD/FULL', () => {
    expect(LoadLevel.MINIMAL).toBe('MINIMAL');
    expect(LoadLevel.STANDARD).toBe('STANDARD');
    expect(LoadLevel.FULL).toBe('FULL');
  });
});

// ── ContextLoader ───────────────────────────────────────────────

describe('ContextLoader', () => {
  let loader: ContextLoader;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'ctx-loader-test-'));
    loader = new ContextLoader();
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  // ── loadRoleContext complexity levels ──────────────────────────

  it('loadRoleContext R01 complexity=0.1 → MINIMAL', () => {
    const ctx = loader.loadRoleContext('R01', 0.1);
    expect(ctx.level).toBe(LoadLevel.MINIMAL);
    expect(ctx.role_id).toBe('R01');
    expect(ctx.loaded_sections).toContain('stance');
    expect(ctx.loaded_sections).not.toContain('thinking_framework');
  });

  it('loadRoleContext R01 complexity=0.5 → STANDARD', () => {
    const ctx = loader.loadRoleContext('R01', 0.5);
    expect(ctx.level).toBe(LoadLevel.STANDARD);
    expect(ctx.loaded_sections).toContain('stance');
    expect(ctx.loaded_sections).toContain('thinking_framework');
    expect(ctx.loaded_sections).not.toContain('loop_guide');
  });

  it('loadRoleContext R01 complexity=0.8 → FULL', () => {
    const ctx = loader.loadRoleContext('R01', 0.8);
    expect(ctx.level).toBe(LoadLevel.FULL);
    expect(ctx.loaded_sections).toContain('stance');
    expect(ctx.loaded_sections).toContain('thinking_framework');
    expect(ctx.loaded_sections).toContain('loop_guide');
  });

  it('MINIMAL tokens < STANDARD tokens < FULL tokens', () => {
    const minCtx = loader.loadRoleContext('R01', 0.1);
    const stdCtx = loader.loadRoleContext('R01', 0.5);
    const fullCtx = loader.loadRoleContext('R01', 0.8);
    expect(minCtx.estimated_tokens).toBeLessThan(stdCtx.estimated_tokens);
    expect(stdCtx.estimated_tokens).toBeLessThan(fullCtx.estimated_tokens);
  });

  it('未知角色使用默认 stance', () => {
    const ctx = loader.loadRoleContext('R99', 0.1);
    expect(ctx.system_prompt).toContain('R99');
    expect(ctx.system_prompt).toContain('未定义角色立场');
    expect(ctx.level).toBe(LoadLevel.MINIMAL);
  });

  // ── estimateTokens ─────────────────────────────────────────────

  it('estimateTokens 空字符串 → 0', () => {
    expect(loader.estimateTokens('')).toBe(0);
  });

  it('estimateTokens ASCII 文本', () => {
    // ASCII: ~0.25 tokens per char. "hello" = 5 chars → ceil(5*0.25) = 2
    const tokens = loader.estimateTokens('hello');
    expect(tokens).toBe(2);
  });

  it('estimateTokens CJK 文本 (中文)', () => {
    // CJK: ~1.5 tokens per char. "你好" = 2 chars → ceil(2*1.5) = 3
    const tokens = loader.estimateTokens('你好');
    expect(tokens).toBe(3);
  });

  // ── buildDocumentIndex ─────────────────────────────────────────

  it('buildDocumentIndex 解析 Markdown', () => {
    const mdPath = join(tmpDir, 'test.md');
    const mdContent = [
      '# Title',
      'Some intro text.',
      '',
      '## Section One',
      'Content of section one.',
      '',
      '## Section Two',
      'Content of section two.',
    ].join('\n');
    writeFileSync(mdPath, mdContent, 'utf-8');

    const index = loader.buildDocumentIndex(mdPath);
    expect(index.doc_path).toBe(mdPath);
    expect(index.sections.length).toBeGreaterThanOrEqual(3);
    expect(index.sections[0].title).toBe('Title');
    expect(index.sections[0].level).toBe(1);
    expect(index.sections[1].title).toBe('Section One');
    expect(index.sections[1].level).toBe(2);
    expect(index.total_lines).toBeGreaterThan(0);
    expect(index.total_tokens).toBeGreaterThan(0);
  });

  // ── loadDocumentSection ────────────────────────────────────────

  it('loadDocumentSection 按标题查找', () => {
    const mdPath = join(tmpDir, 'doc.md');
    const mdContent = [
      '# Overview',
      'Overview content.',
      '',
      '## Installation',
      'Install instructions here.',
      '',
      '## Usage',
      'Usage guide content.',
    ].join('\n');
    writeFileSync(mdPath, mdContent, 'utf-8');

    const section = loader.loadDocumentSection(mdPath, 'Installation');
    expect(section).toBeTruthy();
    expect(section).toContain('Install instructions here.');
  });

  it('loadDocumentSection 不存在 → null', () => {
    const mdPath = join(tmpDir, 'doc2.md');
    writeFileSync(mdPath, '# Hello\nWorld\n', 'utf-8');

    const section = loader.loadDocumentSection(mdPath, 'Nonexistent Section');
    expect(section).toBeNull();
  });
});
