"""Build index.html for the Acme Tasks tour: src/template.tpl + kit + timings -> index.html.

Every beat is derived from the narration's word timings in ../audio/timings.json,
so regenerating a line of voice moves everything anchored to it.

    bin/pvs-py <video_dir>/video/build.py            # signed build (refuses until BRIEF.md is signed)
    bin/pvs-py <video_dir>/video/build.py --draft    # draft: renders and checks, never delivered

Story (BRIEF.md): opening; chapter 1 "Plan your day" (Plan my day reorders the rows by time);
chapter 2 "Add anything" (the New task dialog, a task with a time lands in its slot);
end screen with two cards, then the lockup with the closing line.
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

# What is typed on screen (fictional data, listed in BRIEF.md notes)
TEXTS = {
    "task": "Call the oven repair shop",
    "time": "1:00 PM",
}
ROW = 64            # row height 56 + gap 8 (frontend/styles/tokens.css:36-37)
PLAN_D = 0.42       # --acme-duration-plan 420ms (frontend/styles/tokens.css:47)


def build() -> None:
    b = buildlib.Build(__file__)
    T, w, end = b.T, b.w, b.end

    # ---- Opening: product name and tagline over Today, out of focus ----
    T["open"] = 0.35
    T["N1"] = 0.6                                       # "Maya runs Northwind Bakery ..."
    T["ch1"] = end("N1") + 0.3

    # ---- Chapter 1: plan your day (1x full page) ----
    T["rack1"] = T["ch1"] + 1.5                         # the title holds alone
    T["N2"] = T["rack1"] + 0.2                          # "One click on Plan my day puts every task in order by time."
    T["plan"] = T["N2"] + w("N2", "plan") - 0.15        # the click leads the word "Plan"
    T["reorder"] = T["plan"] + 0.05                     # rows slide to their slots
    b.dur("reorder", PLAN_D)
    T["ch2"] = max(end("N2"), end("reorder")) + 0.8     # hold, then the next title

    # ---- Chapter 2: add anything ----
    T["rack2"] = T["ch2"] + 1.4
    T["addOpen"] = T["rack2"] + 0.35                    # click Add task: the dialog opens
    T["type1"] = T["addOpen"] + 0.45
    T["type1Dur"] = round(len(TEXTS["task"]) / 19.0, 3)  # about 19 characters per second
    b.dur("type1", T["type1Dur"])
    T["timeClick"] = end("type1") + 0.25
    T["type2"] = T["timeClick"] + 0.2
    T["type2Dur"] = round(len(TEXTS["time"]) / 12.0, 3)  # a short entry, one keystroke at a time
    b.dur("type2", T["type2Dur"])
    # "Add a task with a time ..." places "time" on the typed time
    T["N3"] = max(T["type2"] + 0.1 - w("N3", "time"), T["rack2"])
    T["submit"] = max(end("type2") + 0.3, T["N3"] + w("N3", "lands") - 0.25)
    T["land"] = T["submit"] + 0.05                      # dialog closes, the row lands, the toast

    # ---- End screen and lockup ----
    T["endIn"] = max(end("N3") + 0.6, T["land"] + 1.6)
    T["card1"] = T["endIn"] + 0.45
    T["card2"] = T["card1"] + 0.3
    T["lockup"] = T["endIn"] + 1.9
    T["N4"] = T["lockup"] + 0.6                         # after the end screen content has left (0.5 s): no overlap
    T["lkSub"] = T["N4"] + w("N4", "to") - 0.15         # the tagline rises as it is said
    T["end"] = end("N4") + 1.0
    T["DUR"] = round(T["end"] + 0.7, 2)

    # ---- Sound: clicks and typing on the same beats ----
    for t in (T["plan"], T["addOpen"], T["timeClick"], T["submit"]):
        b.click(t)
    b.typing(TEXTS["task"], T["type1"], dur=b.D["type1"])
    b.typing(TEXTS["time"], T["type2"], dur=b.D["type2"], seed=7)
    b.pop(T["land"] + 0.1)

    # ---- Setup beats to snapshot before any render ----
    b.snap(T["open"] + 1.4, "opening title")
    b.snap(T["ch1"] + 0.9, "chapter 1 title")
    b.snap(T["plan"] - 0.05, "cursor on Plan my day, unplanned order")
    b.snap(end("reorder") + 0.3, "planned order and chip")
    b.snap(T["type1"] + b.D["type1"] * 0.6, "dialog at natural size, typing")
    b.snap(end("type2") + 0.1, "both fields typed")
    b.snap(T["land"] + 0.5, "new row in its slot and toast")
    b.snap(T["endIn"] + 1.4, "end screen")
    b.snap(T["lockup"] + 1.4, "lockup")

    b.write(texts=TEXTS)


if __name__ == "__main__":
    buildlib.main_guard(build)
