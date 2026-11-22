# Prompting MiniMax H3 / pi-H3

pi-H3 is a distillation of MiniMax H3, so prompts follow H3's structured format. The official guides are
[base (T2VA/I2VA/FL2VA/L2VA)](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)
and [reference](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md).
The working examples are in [samples/examples.json](../samples/examples.json). This page is a condensed checklist.

> H3 generates **video and audio together**, so describe the sound as well. Speech goes in `<d>` tags.

## Layout

1. **Alignment line**: only when you pass reference images; leave it out for text-only. Follow it with a
   blank line.
2. `integrated_multimodal_description:` the timeline: style, opening composition, actions, camera, speakers,
   dialogue and diegetic sound.
3. `overall_soundscape:` 1–4 sentences covering ambience, action sounds and non-verbal sound. Don't repeat the
   dialogue. Use `N/A` only for total silence.
4. `non_diegetic_music:` 1–3 sentences on instrumentation, tempo and dynamics (not mood words), or `N/A`.

## Alignment lines

| Mode | h3gen flags | Line |
|---|---|---|
| Image to video (first frame) | `--first A` | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| First + last frame | `--first A --last B` | `How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the 0.00-second mark of the target video; <Picture 2> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |
| Last frame only | `--last B` | `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |

`S.SS` is the clip's real duration with two decimals. `h3gen` rounds durations to 17n+5 frames, so a "5 s" clip
is 5.17 s. Copy `duration_s` from a `--dry-run` if you want the exact figure. The Space's 10 s cat example
uses `10.00` for a 10.21 s clip, so rounding to the requested seconds is fine.

## Body rules that matter most

- **Start `[Shot 1]` with the style plus the opening composition**, and for keyframe modes restate what
  `<Picture 1>` shows ("preserving their exact positions: …"). Identity, clothing and colors should match the
  image.
- Write it as a sequence: anchor, then the action starting, then development, then the result. For first+last
  frame: start state, visible intermediate changes, then converging on `<Picture 2>`'s composition. Prefer a
  single shot so the motion can interpolate.
- **Camera:** write the motion in plain English inside the sentence ("The camera holds a static shot", "a slow
  push-in"). Use camera motion instead of a cut for small framing changes.
- **Cuts:** `[Shot 2] At 00:05.000, the camera cuts to …`. The first shot has no timestamp, and later timestamps
  must increase.
- **Speakers:** introduce each speaker with voice cues: `The girlfriend with an offended, sharp, loud voice (S1)
  says: <d>[Spanish] ¿En serio?</d>`. IDs stay the same across shots. Inside `<d>`, put only the language tag and
  the verbatim words. For off-screen voiceover, write "says in an off-screen voiceover", then say the on-screen
  lips stay closed.
- **On-screen text:** put it in double quotes, verbatim.

## Skeletons

Image to video:
```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] <Style>, <what Picture 1 shows, preserving positions/identity>. <Camera>. <Action onset>, <development>, <result>. <Speaker description> (S1) says: <d>[English] <line></d> <Reaction>.

overall_soundscape: <ambience>, <action sounds>.

non_diegetic_music: N/A
```

First + last frame (single shot):
```
How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the 0.00-second mark of the target video; <Picture 2> (from [Shot 1]) aligns with the 5.17-second mark of the target video.

integrated_multimodal_description: [Shot 1] <Style>, the scene shown in <Picture 1>: <start state>. <Camera>. <Subject motion path>, <intermediate changes>, <narrowing differences>. The scene settles into the exact composition, lighting, and framing of <Picture 2>.

overall_soundscape: <…>

non_diegetic_music: <instrumentation, tempo, dynamics | N/A>
```

## pi-H3-specific tips

- Two steps is the Space default and is enough for simple scenes. Use `--steps 4` (needs the `full` profile)
  for busy scenes, fine motion or text.
- Draft at `--megapixels 0.25–0.5` with a fixed seed, then re-run at 1.0. The composition changes with
  resolution, so expect differences rather than an exact upscale.
- To compare settings, fix the seed and change one thing at a time; record the results in work-notes/.
