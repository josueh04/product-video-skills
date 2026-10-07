"""Build index.html for this video: src/template.tpl + kit + timings -> index.html.

Every beat is derived from the narration's word timings in ../audio/timings.json,
so regenerating a line of voice moves everything anchored to it.

    bin/pvs-py <video_dir>/video/build.py            # signed build (refuses until BRIEF.md is signed)
    bin/pvs-py <video_dir>/video/build.py --draft    # draft: renders and checks, never delivered
    ... --draft --fake-timings                       # layout draft before any voice exists

This file is an example to rewrite for your video: two chapters, a pop-up, typing, a
toast, a gentle push-in, the end screen and the lockup. The lines are in ../audio/lines.tsv.
"""
import os
import sys
from pathlib import Path


def _workbench() -> Path:
    env = os.environ.get("PVS_HOME")
    if env and (Path(env) / "bin" / "pvs-py").exists():
        return Path(env)
    for d in Path(__file__).resolve().parents:
        if (d / "bin" / "pvs-py").exists():
            return d
    sys.exit("Cannot find the workbench: run this with <workbench>/bin/pvs-py or set PVS_HOME.")


sys.path.insert(0, str(_workbench() / "skills" / "ui-demo-composer" / "scripts"))
import buildlib  # noqa: E402

# What the user types on screen (fictional data only, approved in BRIEF.md notes)
TEXTS = {
    "t1": "Call the supplier at 3 pm",
}


def build() -> None:
    b = buildlib.Build(__file__)
    T, w, end = b.T, b.w, b.end

    # ---- Opening: who this is for, over the product out of focus ----
    T["open"] = 0.35                                   # logo, product name, one line
    T["ch1"] = 2.3                                     # the opening leaves, chapter 1 title enters

    # ---- Chapter 1: the plan is ready (1x full page) ----
    T["N1"] = T["ch1"] + 0.3                           # "Every morning, your plan ..."
    # focus returns just before "plan", but the title holds at least 1.4 s (titles are pauses)
    T["rack1"] = max(T["N1"] + w("N1", "plan") - 0.25, T["ch1"] + 1.4)
    T["open1"] = T["N1"] + w("N1", "ready") - 0.1      # a task is opened on "ready": details pop-up
    T["close1"] = max(end("N1") + 0.2, T["open1"] + 1.4)

    # ---- Chapter 2: add anything (one gentle push-in, made behind the title) ----
    T["ch2"] = T["close1"] + 0.8                       # hold about 0.8 s, then the next title
    T["rack2"] = T["ch2"] + 1.1                        # the title holds alone
    T["N2"] = T["rack2"] + 0.1                         # narration starts as focus returns
    b.cam(T["ch2"] + 0.6, 1.2, "#addRow", d=0.4, label="push to the add field while out of focus")
    T["inClick"] = T["N2"] + w("N2", "type") - 0.05
    T["type1"] = T["inClick"] + 0.25
    T["type1Dur"] = round(len(TEXTS["t1"]) / 17.0, 3)  # 17 characters per second
    b.dur("type1", T["type1Dur"])
    T["add"] = max(end("type1") + 0.3, T["N2"] + w("N2", "lands") - 0.1)

    # ---- End screen and lockup ----
    T["endIn"] = max(end("N2") + 0.6, T["add"] + 1.4)
    b.cam(T["endIn"] + 0.3, 1.0, d=0.8, label="back to 1x behind the end screen")
    T["card1"] = T["endIn"] + 0.45
    T["card2"] = T["card1"] + 0.3
    T["card3"] = T["card2"] + 0.3
    T["lockup"] = T["endIn"] + 1.9
    T["end"] = T["lockup"] + 1.8
    T["DUR"] = round(T["end"] + 0.7, 2)

    # ---- Sound: clicks and typing on the same beats ----
    for t in (T["open1"], T["close1"], T["inClick"]):
        b.click(t)
    b.typing(TEXTS["t1"], T["type1"], dur=T["type1Dur"])
    b.click(T["add"], vol=0.25)

    # ---- Setup beats to snapshot before any render ----
    b.snap(T["ch1"] + 0.9, "chapter 1 title")
    b.snap(T["rack1"] + 1.0, "chapter 1 framing, cursor")
    b.snap(T["open1"] + 0.5, "pop-up at natural size")
    b.snap(T["type1"] + T["type1Dur"] * 0.6, "chapter 2 push-in, typing")
    b.snap(T["add"] + 0.5, "new row and toast")
    b.snap(T["endIn"] + 1.4, "end screen")
    b.snap(T["lockup"] + 1.4, "lockup")

    b.write(texts=TEXTS)


if __name__ == "__main__":
    buildlib.main_guard(build)
