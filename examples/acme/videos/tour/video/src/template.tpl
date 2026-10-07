<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1920, height=1080">
    <title>{{PRODUCT_NAME}} tour</title>
    {{GSAP}}
    <style>
{{FONTS_CSS}}
{{STAGE_CSS}}
{{STAGE_VARS}}
{{TITLES_CSS}}
{{TOKENS_CSS}}
{{UI_CSS}}
{{APP_CSS}}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{{DUR}}" data-fps="{{FPS}}" data-width="1920" data-height="1080">
      <div id="stage">
        <div id="camera">
          <div id="blurWrap">
            <div id="app">
              <!-- SHELL and TODAY: specs/today.html (frontend/index.html:12-42) -->
              <div class="shell">
                <aside class="sidebar">
                  <div class="brand"><img src="{{APP_TILE}}" alt=""><span class="brand-name">{{PRODUCT_NAME}}</span></div>
                  <nav class="nav">
                    <div class="nav-item is-active"><i data-icon="acme-sun" class="icon"></i><span>Today</span></div>
                    <div class="nav-item"><i data-icon="acme-calendar" class="icon"></i><span>Upcoming</span></div>
                    <div class="nav-item"><i data-icon="acme-folder" class="icon"></i><span>Projects</span></div>
                  </nav>
                </aside>
                <main class="main">
                  <header class="page-head">
                    <h1 class="page-title">Today</h1><span class="page-date">Tuesday, March 3</span>
                    <div class="page-actions">
                      <div class="btn btn-secondary" id="addTaskBtn"><i data-icon="acme-plus" class="icon"></i><span>Add task</span></div>
                      <div class="btn btn-primary" id="planBtn"><i data-icon="acme-sparkle" class="icon"></i><span>Plan my day</span></div>
                    </div>
                  </header>
                  <div class="list-meta"><span id="count4">4 tasks</span><span id="count5">5 tasks</span><span class="planned-chip" id="plannedChip"><i data-icon="acme-clock" class="icon"></i><span>Planned by time</span></span></div>
                  <ul class="task-list" id="taskList">
                    <li class="task" id="rowCake"><span class="task-check"></span><span class="task-title">Confirm the cake order with Omar Haddad</span><span class="task-project">Orders</span><span class="task-time">11:30 AM</span></li>
                    <li class="task" id="rowFlour"><span class="task-check"></span><span class="task-title">Order flour for Saturday</span><span class="task-project">Supplies</span><span class="task-time">2:00 PM</span></li>
                    <li class="task" id="rowBread"><span class="task-check"></span><span class="task-title">Bake the morning bread</span><span class="task-project">Kitchen</span><span class="task-time">6:00 AM</span></li>
                    <li class="task" id="rowInvoices"><span class="task-check"></span><span class="task-title">Send the weekly invoices</span><span class="task-project">Office</span><span class="task-time">4:30 PM</span></li>
                    <li class="task" id="rowNew"><span class="task-check"></span><span class="task-title">{{TEXT_TASK}}</span><span class="task-time">{{TEXT_TIME}}</span></li>
                  </ul>
                </main>
              </div>

              <!-- ADD TASK DIALOG: specs/add-dialog.html (frontend/index.html:46-77) -->
              <div class="pvs-modal" id="pop1">
                <div class="pvs-backdrop"></div>
                <div class="pvs-box dialog">
                  <div class="dialog-head"><h2 class="dialog-title">New task</h2><span class="icon-btn"><i data-icon="acme-x" class="icon"></i></span></div>
                  <div class="field"><span class="field-label">Task</span><div class="input" id="inTask"><span class="ph" id="phTask">What needs doing?</span><span class="val" id="valTask"></span></div></div>
                  <div class="field-row">
                    <div class="field field-time"><span class="field-label">Time</span><div class="input" id="inTime"><span class="ph" id="phTime">e.g. 3:00 PM</span><span class="val" id="valTime"></span></div></div>
                    <div class="field field-project"><span class="field-label">Project</span><div class="input select"><span>No project</span><span class="chev"></span></div></div>
                  </div>
                  <div class="dialog-foot"><div class="btn btn-ghost">Cancel</div><div class="btn btn-primary" id="addSubmit">Add task</div></div>
                </div>
              </div>

              <!-- TOAST: toast.added (frontend/i18n/en.json:21) -->
              <div class="pvs-toast-slot"><div class="pvs-toast toast" id="toast1">Added to Today at {{TEXT_TIME}}</div></div>
              <div class="pvs-rip" id="pvsRip"></div>
              <div class="pvs-cur" id="pvsCur"></div>
            </div>
          </div>
        </div>

        <!-- ====== SCREEN-SPACE LAYERS (1920x1080) ====== -->
        <div id="veil"></div>
        <div class="pvs-ttl" id="tOpen">
          <div class="pvs-mask"><img class="pvs-ln pvs-opLogo" src="{{LOGO_ON_VEIL}}" alt=""></div>
          <div class="pvs-mask"><div class="pvs-ln pvs-opT">{{PRODUCT_NAME}}</div></div>
          <div class="pvs-mask"><div class="pvs-ln pvs-opS">The to-do list that plans your day.</div></div>
        </div>
        <div class="pvs-ttl" id="tCh1"><div class="pvs-mask"><div class="pvs-ln pvs-chT">Plan <em>your day.</em></div></div></div>
        <div class="pvs-ttl" id="tCh2"><div class="pvs-mask"><div class="pvs-ln pvs-chT">Add <em>anything.</em></div></div></div>
        <div id="endS">
          <div class="pvs-end-bg"></div>
          <div class="pvs-end-content">
            <div class="pvs-eHead" id="eHead"><div class="pvs-mask"><div class="pvs-ln">One list, <em>planned for you.</em></div></div></div>
            <!-- each card names one capability from COVERAGE.md and carries a real UI piece -->
            <div class="pvs-cards">
              <div class="pvs-card" id="card1"><div class="pvs-card-h">Plans your day</div><div class="pvs-card-s">One click, in order by time</div>
                <div class="pvs-card-ui">
                  <span class="planned-chip"><i data-icon="acme-clock" class="icon"></i><span>Planned by time</span></span>
                  <div class="task"><span class="task-check"></span><span class="task-title">Bake the morning bread</span><span class="task-time">6:00 AM</span></div>
                  <div class="task"><span class="task-check"></span><span class="task-title">Confirm the cake order</span><span class="task-time">11:30 AM</span></div>
                </div></div>
              <div class="pvs-card" id="card2"><div class="pvs-card-h">Finds the slot</div><div class="pvs-card-s">New tasks land by their time</div>
                <div class="pvs-card-ui">
                  <div class="task"><span class="task-check"></span><span class="task-title">{{TEXT_TASK}}</span><span class="task-time">{{TEXT_TIME}}</span></div>
                  <div class="toast" style="margin-top: 14px;">Added to Today at {{TEXT_TIME}}</div>
                </div></div>
            </div>
          </div>
        </div>
        <div id="lock">
          <img class="pvs-lkLogo" src="{{LOGO_ON_VEIL}}#lockup" alt="">
          <div class="pvs-lkT">{{PRODUCT_NAME}}</div>
          <div class="pvs-lkS">The to-do list that plans your day.</div>
        </div>
        <div id="fade"></div>
      </div>

    {{AUDIO}}
    </div>

    <script>
      const T = (window.PVS_T = {{T_JSON}});
{{STAGE_JS}}

      PVS.ready((S) => {
        const tl = S.tl;
        const easeApp = PVS.bez(0.2, 0, 0, 1);              /* --acme-ease-out (frontend/styles/tokens.css:48) */
        const ROW = 64;                                       /* row 56 + gap 8 */

        /* ---------- initial states ---------- */
        S.init(["#rowCake", "#rowFlour", "#rowBread", "#rowInvoices"], { y: 0 });
        S.init("#rowNew", { opacity: 0, y: -2 * ROW + 6 });

        /* ---------- opening ---------- */
        S.fadeFromBlack(0.1);
        S.title("#tOpen", [T.open, T.open + 0.15, T.open + 0.6], T.ch1 - 0.05);

        /* ---------- chapter 1: plan your day (1x full page) ---------- */
        S.chapter("#tCh1", { at: T.ch1, rack: T.rack1, blurred: true });
        S.cursorShow(T.rack1 + 0.05);
        S.clickOn("#planBtn", T.plan, { hover: "hov", unhover: T.plan + 0.3 });
        /* planDay(): rows slide to their time slot, 420 ms (frontend/app.js:72-88) */
        [["#rowCake", ROW], ["#rowFlour", ROW], ["#rowBread", -2 * ROW]].forEach(([sel, dy]) => {
          tl.fromTo(sel, { y: 0 }, { y: dy, duration: 0.42, ease: easeApp, immediateRender: false }, T.reorder);
        });
        S.show("#plannedChip", T.reorder, "inline-flex");

        /* ---------- chapter 2: add anything ---------- */
        S.chapter("#tCh2", { at: T.ch2, rack: T.rack2 });
        S.clickOn("#addTaskBtn", T.addOpen, { hover: "hov", unhover: T.addOpen + 0.2, travel: 0.5 });
        S.popupOpen("#pop1", T.addOpen, { scale: 0.97, y: 8, d: 0.2, delay: 0.02, ease: easeApp });  /* dialog-in 200 ms */
        S.state("#inTask", "foc", T.addOpen + 0.02);
        S.hide("#phTask", T.type1);
        S.type("#valTask", T.texts.task, T.type1, T.type1Dur);
        S.clickOn("#inTime", T.timeClick, { travel: 0.4, dx: -40 });
        S.state("#inTask", null, T.timeClick);
        S.state("#inTime", "foc", T.timeClick);
        S.hide("#phTime", T.type2);
        S.type("#valTime", T.texts.time, T.type2, T.type2Dur);
        S.clickOn("#addSubmit", T.submit, { hover: "hov", travel: 0.5 });
        /* addTask(): the dialog closes at once, the list re-renders with the new row in its slot (frontend/app.js:90-100) */
        S.hide("#pop1", T.land);
        S.set("#rowFlour", { y: 2 * ROW }, T.land);
        S.set("#rowInvoices", { y: ROW }, T.land);
        S.show("#rowNew", T.land, "flex");
        tl.fromTo("#rowNew", { opacity: 0, y: -2 * ROW + 6 }, { opacity: 1, y: -2 * ROW, duration: 0.2, ease: easeApp, immediateRender: false }, T.land);
        S.hide("#count4", T.land);
        S.show("#count5", T.land, "inline");
        S.toast("#toast1", T.land + 0.05, 1.5, { y: 0 });

        /* ---------- end screen and lockup ---------- */
        S.cursorHide(T.endIn - 0.4);
        S.endScreen(T.endIn, { head: ["#eHead", T.endIn + 0.2], cards: [["#card1", T.card1], ["#card2", T.card2]] });
        S.lockup(T.lockup, { title: T.N4 - 0.05, sub: T.lkSub });
        S.fadeToBlack(T.end);
      });
    </script>
  </body>
</html>
