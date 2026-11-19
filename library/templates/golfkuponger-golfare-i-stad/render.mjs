// Golfare i <stad>? som dashboardmall: en JPG i 9:16 och en i 4:5 med det gemensamma skelettet.
//   node library/templates/golfkuponger-golfare-i-stad/render.mjs --lokal --satt stad=Uppsala --satt klubb=Upsala --bildmapp <mapp> --satt bakgrund=foto.jpg
// Filmerna (slam, snurr) görs med rendera.mjs.
import { cli } from '../_mall/render-bas.mjs';
await cli(import.meta.url);
