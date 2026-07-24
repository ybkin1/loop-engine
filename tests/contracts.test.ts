import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { HostAdapterQoder, HostAdapterStandalone, createHostAdapter } from '../src/core/contracts.js';
import { EnforcementLevel, HOST_PRESETS } from '../src/core/enforcement.js';

// ── HostAdapterQoder ─────────────────────────────────────────────────────────

describe('HostAdapterQoder', () => {
  let adapter: HostAdapterQoder;
  let tempDir: string;

  beforeEach(() => {
    adapter = new HostAdapterQoder();
    tempDir = mkdtempSync(join(tmpdir(), 'contracts-test-'));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('host_name = "qoder"', () => {
    expect(adapter.host_name).toBe('qoder');
  });

  it('enforcement_level = STRONG', () => {
    expect(adapter.enforcement_level).toBe(EnforcementLevel.STRONG);
  });

  it('capabilities 匹配 HOST_PRESETS.qoder', () => {
    expect(adapter.capabilities).toEqual(HOST_PRESETS.qoder);
  });

  it('read_file 读取存在的文件返回内容', () => {
    const testFile = join(tempDir, 'test.txt');
    writeFileSync(testFile, 'hello world', 'utf-8');
    const content = adapter.read_file(testFile);
    expect(content).toBe('hello world');
  });

  it('read_file 读取不存在的文件返回 null', () => {
    const nonExistent = join(tempDir, 'nonexistent.txt');
    const content = adapter.read_file(nonExistent);
    expect(content).toBeNull();
  });

  it('file_exists 返回 true/false', () => {
    const testFile = join(tempDir, 'exists.txt');
    expect(adapter.file_exists(testFile)).toBe(false);
    writeFileSync(testFile, 'content', 'utf-8');
    expect(adapter.file_exists(testFile)).toBe(true);
  });

  it('write_file 写入并验证', () => {
    const testFile = join(tempDir, 'write.txt');
    const result = adapter.write_file(testFile, 'test content');
    expect(result).toBe(true);
    expect(existsSync(testFile)).toBe(true);
    expect(adapter.read_file(testFile)).toBe('test content');
  });

  it('execute 执行简单命令', async () => {
    // Windows 使用 cmd /c echo
    const result = await adapter.execute('echo test');
    expect(result.exit_code).toBe(0);
    expect(result.stdout.trim()).toContain('test');
  });

  it('freeze_evidence 返回 hash', () => {
    const evidence = adapter.freeze_evidence('ev1', 'content');
    expect(evidence.evidence_id).toBe('ev1');
    expect(evidence.content_hash).toBeDefined();
    expect(evidence.content_hash.length).toBe(64); // SHA256 hex
    expect(evidence.frozen_at).toBeDefined();
  });
});

// ── HostAdapterStandalone ────────────────────────────────────────────────────

describe('HostAdapterStandalone', () => {
  let adapter: HostAdapterStandalone;

  beforeEach(() => {
    adapter = new HostAdapterStandalone();
  });

  it('host_name = "standalone"', () => {
    expect(adapter.host_name).toBe('standalone');
  });

  it('enforcement_level = ADVISORY', () => {
    expect(adapter.enforcement_level).toBe(EnforcementLevel.ADVISORY);
  });

  it('read_file 返回 null', () => {
    const content = adapter.read_file('/any/path.txt');
    expect(content).toBeNull();
  });

  it('execute 返回 exit_code -1', async () => {
    const result = await adapter.execute('echo test');
    expect(result.exit_code).toBe(-1);
    expect(result.stderr).toBe('no host');
  });

  it('present_gate 返回 TIMEOUT', async () => {
    const decision = await adapter.present_gate('gate1', ['cond1']);
    expect(decision.decision).toBe('TIMEOUT');
    expect(decision.actor).toBe('system');
  });
});

// ── createHostAdapter ────────────────────────────────────────────────────────

describe('createHostAdapter', () => {
  it('createHostAdapter("qoder") 返回 HostAdapterQoder', () => {
    const adapter = createHostAdapter('qoder');
    expect(adapter).toBeInstanceOf(HostAdapterQoder);
    expect(adapter.host_name).toBe('qoder');
  });

  it('createHostAdapter("unknown") 返回 HostAdapterStandalone', () => {
    const adapter = createHostAdapter('unknown');
    expect(adapter).toBeInstanceOf(HostAdapterStandalone);
    expect(adapter.host_name).toBe('standalone');
  });
});
