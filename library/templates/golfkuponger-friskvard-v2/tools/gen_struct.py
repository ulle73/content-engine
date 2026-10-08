"""ACE-Step generation with structure tags (instrumental). Run from the ACE-Step dir:
  uv run --no-sync python <this> <out_dir> <seconds>
Generates several takes with section tags so the arrangement has a build, a drop and a final chord."""
import os, shutil, sys, time
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

root = os.getcwd()
out_dir, seconds = sys.argv[1], int(sys.argv[2])
os.makedirs(out_dir, exist_ok=True)
tmp = os.path.join(root, "output"); os.makedirs(tmp, exist_ok=True)

TAKES = [
    ("e", "premium cinematic electronic pop advert, warm analog synth pads, filtered build with snare roll and riser, "
          "huge drop with punchy kick, sub bass and bright plucks, confident, Scandinavian, polished commercial mix",
     "[Intro]\n[Build-up]\n[Drop]\n[Chorus]\n[Outro]", 124, "A minor", 11),
    ("f", "uplifting modern sports commercial, tight drums, claps, deep bass, bright synth lead hook, rising tension "
          "intro then explosive drop, euphoric, clean professional master, ends on one big sustained chord",
     "[Intro]\n[Build-up]\n[Drop]\n[Chorus]\n[Outro]", 120, "C major", 23),
    ("g", "stylish confident house groove for a premium brand film, crisp hats, rolling bassline, piano stabs, "
          "short riser then drop, golden summer feeling, polished, final chord ring-out",
     "[Intro]\n[Build-up]\n[Drop]\n[Verse]\n[Outro]", 122, "F major", 37),
]
if len(sys.argv) > 3:
    TAKES = [t for t in TAKES if t[0] in sys.argv[3]]

dit = AceStepHandler()
dit.initialize_service(project_root=root, config_path="acestep-v15-turbo", device="cpu")
for name, cap, lyr, bpm, key, seed in TAKES:
    t = time.time()
    p = GenerationParams(caption=cap, lyrics=lyr, instrumental=True, duration=seconds, bpm=bpm,
                         keyscale=key, timesignature="4", seed=seed, thinking=False)
    r = generate_music(dit, LLMHandler(), p, GenerationConfig(batch_size=1, audio_format="wav", use_random_seed=False, seeds=[seed]), save_dir=tmp)
    if not r.success:
        print("ERR", name, r.error); continue
    dst = os.path.join(out_dir, f"track-{name}.wav")
    shutil.copy(r.audios[0]["path"], dst)
    print(f"OK {name} {time.time()-t:.0f}s -> {dst}", flush=True)
