// Pre-render browser QA: `hyperframes check --json` (lint + runtime + layout + WCAG contrast in one browser session)
// plus the runtime's own "[cut-layout]" report of the measured text boxes → safe-zone, typography and font warnings.
import { checkSafeZones, describeViolations } from './safezones.js';

/** Parse the JSON envelope of `hyperframes check --json`. Returns the parsed object or null. */
export function parseCheck(stdout) {
  const text = String(stdout || '').replace(/\x1b\[[0-9;]*m/g, '');
  const start = text.indexOf('{');
  if (start < 0) return null;
  try {
    return JSON.parse(text.slice(start));
  } catch {
    return null;
  }
}

/** The runtime's layout report (last "[cut-layout] {...}" console line). */
export function layoutReport(check) {
  const findings = check?.runtime?.findings || [];
  let report = null;
  for (const f of findings) {
    const msg = String(f.message || '');
    const at = msg.indexOf('[cut-layout] ');
    if (at < 0) continue;
    try { report = JSON.parse(msg.slice(at + 13)); } catch { /* ignore */ }
  }
  return report;
}

/**
 * check envelope + format → {warnings, lintErrors, layout, safe: [violations], contrast: [findings]}.
 * Only real problems become warnings; our own layout report line is not a problem.
 */
export function judgeCheck(check, format) {
  const warnings = [];
  const lintErrors = (check?.lint?.findings || []).filter((f) => f.severity === 'error');
  if (lintErrors.length) {
    warnings.push(`HyperFrames lint: ${lintErrors.length} fel (${lintErrors.map((e) => e.code || e.message).join(', ')}).`.slice(0, 300));
  }
  const runtimeErrors = (check?.runtime?.findings || []).filter((f) => f.severity === 'error');
  if (runtimeErrors.length) {
    warnings.push(`HyperFrames körfel: ${runtimeErrors.map((e) => String(e.message || e.code)).join(' | ')}`.slice(0, 300));
  }
  const layout = layoutReport(check);
  let safe = [];
  if (layout) {
    const boxes = (layout.texts || []).filter((t) => t.box).map((t) => ({ id: t.id, ...t.box }));
    safe = checkSafeZones(boxes, format);
    warnings.push(...describeViolations(safe, format));
    for (const t of layout.texts || []) {
      if (t.forced) warnings.push(`Typografi: texten i scen ${t.id} är för lång för formatet och sattes i ${t.fs} px – korta den.`);
    }
    if (layout.missingFonts?.length) warnings.push(`Typsnitt laddades inte: ${layout.missingFonts.join(', ')}.`);
  }
  const contrast = (check?.contrast?.findings || []).filter((f) => f.severity === 'error' || f.severity === 'warning');
  if (contrast.length) {
    const sample = contrast.slice(0, 3).map((f) => {
      const ratio = f.ratio ?? f.contrastRatio ?? f.contrast;
      return `"${String(f.text || '').slice(0, 24)}"${ratio ? ` ${Number(ratio).toFixed(1)}:1` : ''}`;
    }).join(', ');
    warnings.push(`Kontrast: ${contrast.length} textställen under WCAG AA (${sample}).`.slice(0, 300));
  }
  const overflow = (check?.layout?.findings || []).filter((f) => f.severity === 'error');
  if (overflow.length) warnings.push(`Layout: ${overflow.length} fel (${[...new Set(overflow.map((f) => f.code))].join(', ')}).`.slice(0, 300));
  return { warnings, lintErrors, layout, safe, contrast };
}
