// Testmallen renderas med det gemensamma skelettet: node library/templates/_mall/testmall/render.mjs --lokal
import { cli } from '../render-bas.mjs';
await cli(import.meta.url);
