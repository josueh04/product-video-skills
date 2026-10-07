# Reading sheets, strips and the numbers

## Contact sheets (`qa/sheets/sheet-NN.jpg`)

16 frames per sheet, one per second, labelled with the time in the top-left corner.

- Read them in order as a storyboard: does each chapter open with context, show one idea,
  and hold about 0.8 s before the next? A sheet where three frames in a row look different
  in several places is a beat that changes too much at once.
- Look for: text cut by a frame edge, a pop-up not centred or not whole, a field that is empty
  or shows a placeholder, a cursor outside the frame, a wrong or fallback font, a hand-drawn
  icon, an old product name, real-looking personal data, a vendor logo.
- **The label can cover a title.** Before calling a top-left title cut, pull the full frame:
  `ffmpeg -ss <t> -i <mp4> -frames:v 1 frame.png`. Two "cut" titles in one review were the label.
- A sheet samples one frame per second. Anything shorter than a second can fall between two
  samples, so the sheets prove what is there, never what is absent.

## Strips (`qa/strips/<name>.jpg`)

Four columns, every frame labelled with its time to the millisecond.

- Make one for every transition: modal open and close, scroll, camera move, chapter title in
  and out, every beat that changed in this version, the end screen to the lockup. Default
  6 fps; 8 to 10 fps for a doubtful spot.
- What a strip catches: a flash of the next screen before a fade (a 0.3 s UI flash before a
  lockup was found at 6 fps), ghost text from a menu that should have closed a frame before a
  modal opened, a modal clipped by the frame during its scale-in, a cursor reset landing
  inside the next move, a scroll that overshoots the end of its column.
- For a small region, crop instead of scaling the whole frame:
  `ffmpeg -ss 39 -t 2 -i <mp4> -vf "fps=8,crop=1100:500:820:150" crop_%02d.png`.
- `qa.py` makes one strip per outlier run (10 fps, 0.5 s around it) and one of the last 5 s.
  Those are a start, not the set: the transitions are yours to list.

## Outlier runs

`REPORT.md` lists each run with its time span, frame count and the count of frames per index
mod 3. `[n, 0, 0]` with n of 4 or more is the worker pattern (a seek-safety bug, never a
false positive). Mixed mods are usually motion; confirm with a strip at 10 fps:

- continuous motion (a scroll whose per-frame offset ramps 0 to 19 to 0 px, a camera easing
  back after a modal) is fine;
- one frame that shows something neither neighbour shows is a glitch, whatever its mod.

## Audio numbers

- `edges.py` prints, for every narration clip, the peak level of the mix in the 120 ms before
  it starts (`pre`), its first 120 ms (`head`) and the 120 ms after it ends (`post`), plus two
  numbers read from the clip file: `tail`, its last 40 ms, and `gap`, the silence after its last
  sample above -50 dBFS. A clean ending is 45 dB or more down in that window, inside the 80 ms
  fade the voice script applies; a loud `tail` with a near-zero `gap` means the clip was cut
  while speaking. A wider window read the natural decay of clean lines as "loud" and flagged
  all of them. A `post` jump with nothing scheduled there is a click. Listen at those times in
  the mix, not in the clip files.
- Clicks inside a voice clip are almost always consonants (a hard "k"): check the word
  timings at that second before calling it a defect.

## Parity (`parity.py`)

Both renders decoded at 192x108 gray, 30 fps, compared frame by frame. Encoding noise stays
under about 0.1; a stretch above 1.0 changed. Use `--skip A:B` for every beat that changed on
purpose and expect the rest to stay under 1.0 (two real re-renders measured maxima of 0.062
and 0.085 outside their edited beats). `--audio` compares 100 ms RMS levels too.

## Numeric checks for one question

When one question needs proof, measure instead of eyeballing:

- **Is a title present?** Count bright pixels in its band across frames (a title band went
  from 43,523 bright pixels to 0 on the frames one worker rendered).
- **Did a fade expose UI?** Mean luma per frame across the transition: a bump before the
  lockup is the flash.
- **What moved?** The bounding box of the difference between consecutive frames: a box that
  slides smoothly is a camera move, a box that blinks is a glitch.
- **Is a color right?** Sample the pixel at full resolution, not from a scaled sheet.
