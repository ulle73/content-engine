// Library id → native treatment of the cut template. The same file drives the Python warnings (engine/edit/spec.py).
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const SUPPORT = JSON.parse(readFileSync(join(HERE, '..', 'support.json'), 'utf8'));

const SINGULAR = { transitions: 'transition', effects: 'effect', text: 'text' };
const INDEX = {};
for (const group of Object.keys(SINGULAR)) {
  INDEX[group] = {};
  for (const [native, entry] of Object.entries(SUPPORT[group])) {
    INDEX[group][`cut.${SINGULAR[group]}.${native}`] = native;
    for (const id of entry.ids) INDEX[group][id] = native;
  }
}

export function resolve(group, id) {
  if (!id) return null;
  return INDEX[group][id] || null;
}

export function transitionDuration(native) {
  return SUPPORT.transitions[native]?.duration ?? 0.5;
}
