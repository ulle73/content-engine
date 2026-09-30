/** Original registered animation. No expressions, remote assets, or user-supplied JSON. */
export const mark = {
  v: "5.7.4",
  fr: 30,
  ip: 0,
  op: 90,
  w: 400,
  h: 400,
  nm: "Content Engine orbit",
  ddd: 0,
  assets: [],
  layers: [
    {
      ddd: 0,
      ind: 1,
      ty: 4,
      nm: "Orbit",
      sr: 1,
      ks: {
        o: { a: 0, k: 100 },
        r: {
          a: 1,
          k: [
            {
              t: 0,
              s: [-90],
              e: [270],
              i: { x: [0.4], y: [1] },
              o: { x: [0.4], y: [0] },
            },
            { t: 90, s: [270] },
          ],
        },
        p: { a: 0, k: [200, 200, 0] },
        a: { a: 0, k: [0, 0, 0] },
        s: { a: 0, k: [100, 100, 100] },
      },
      ao: 0,
      shapes: [
        {
          ty: "el",
          d: 1,
          s: { a: 0, k: [250, 250] },
          p: { a: 0, k: [0, 0] },
          nm: "Ring",
        },
        {
          ty: "st",
          c: { a: 0, k: [0.91, 0.97, 0.94, 1] },
          o: { a: 0, k: 100 },
          w: { a: 0, k: 10 },
          lc: 2,
          lj: 2,
          nm: "Stroke",
        },
        {
          ty: "tm",
          s: { a: 0, k: 0 },
          e: {
            a: 1,
            k: [
              {
                t: 0,
                s: [0],
                e: [90],
                i: { x: [0.3], y: [1] },
                o: { x: [0.3], y: [0] },
              },
              { t: 60, s: [90] },
            ],
          },
          o: { a: 0, k: 0 },
          m: 1,
          nm: "Draw",
        },
      ],
      ip: 0,
      op: 90,
      st: 0,
      bm: 0,
    },
  ],
};
