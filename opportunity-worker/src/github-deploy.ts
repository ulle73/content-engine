export function isAutoDeployTarget(repo: string, branch: string, raw: string): boolean {
  const target = repo + "@" + branch;
  return new Set(raw.split(",").map((value) => value.trim()).filter(Boolean)).has(target);
}
