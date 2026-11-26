// Blink för Golfkuponger (2026-11-26): enkel grafik som växlar mellan två färger. Renderas med det gemensamma skelettet
// (library/templates/_mall/render-bas.mjs); reglagen står i mall.json.
//   node render.mjs --lokal [--format 9x16,4x5] [--satt stor=6] [--satt "rad2=Dagar kvar av året"] [--ut dir]
// Ut: <ut>/golfkuponger-blink-<format>.mp4 (loopar sömlöst; Spotlight-slutbilden bara med --satt slutbild=true),
// <ut>/golfkuponger-blink-<format>.gif (ett blink, loopar i det oändliga – för mejl, webb och chatt; Meta tar mp4:an)
// och <ut>/golfkuponger-blink-<format>.jpg (stillbilden = läge a: grönt bakom, guld i texten).
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { cli, ROT } from '../_mall/render-bas.mjs';

const ff = a => execFileSync('ffmpeg', ['-v', 'error', '-y', ...a]);
const outro = format => path.join(ROT, `edit-renderer/outros/golfkuponger/spotlight-${format}.mp4`);

function efterVideo({ fil, info, format }) {
  const LEN = info.langd, tmp = fil.replace(/\.mp4$/, '.tmp.mp4');
  const slut = info.slutbild && fs.existsSync(outro(format)) ? outro(format) : null;
  const varningar = info.slutbild && !slut ? [`Slutbilden saknas för ${format}.`] : [];
  if (slut) {
    const [W, H] = format === '4x5' ? [1080, 1350] : [1080, 1920];
    ff(['-i', fil, '-i', slut, '-filter_complex',
      `anullsrc=r=48000:cl=stereo,atrim=0:${LEN}[a0];[0:v]fps=30,format=yuv420p,setsar=1[v0];` +
      `[1:v]scale=${W}:${H},fps=30,format=yuv420p,setsar=1[v1];[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1];` +
      '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]',
      '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', '30',
      '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', tmp]);
    fs.renameSync(tmp, fil);
  }
  ff(['-i', fil, '-f', 'null', '-']);   // leveransfilen ska gå att avkoda
  if (!slut) {
    // gif: exakt två bilder (läge a och läge b, mitt i var sin period) med 1/takt s var, loopar i det oändliga.
    // Egen palett per bild (grönt och guld delar annars 256 färger och bandar).
    const gif = fil.replace(/\.mp4$/, '.gif'), n = Math.round(info.period * 30);
    ff(['-i', fil, '-filter_complex',
      `[0:v]select='eq(n,${n >> 1})+eq(n,${n + (n >> 1)})',setpts=N/(${(1 / info.period).toFixed(6)}*TB),split[a][b];` +
      '[a]palettegen=stats_mode=single:max_colors=256[p];[b][p]paletteuse=new=1:dither=sierra2_4a',
      '-r', (1 / info.period).toFixed(6), '-loop', '0', gif]);
  }
  return { varningar: [...(info.varningar || []), ...varningar] };
}

await cli(import.meta.url, { efterVideo });
