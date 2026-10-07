<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1920, height=1080">
    <title>{{PRODUCT_NAME}} demo</title>
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
              <!-- ====== THE PRODUCT UI ======
                   Replace this example shell with the screens rebuilt from specs/ (one comment per
                   block naming its source component). Shared pieces of the product belong in
                   products/<slug>/kit/ui/<name>.html and are included with a UI:name placeholder in double braces. -->
              <aside class="side">
                <div class="side-logo"><img src="{{APP_TILE}}" alt=""></div>
                <div class="nav sel">Today</div>
                <div class="nav">Upcoming</div>
                <div class="nav">Projects</div>
              </aside>
              <main class="main">
                <header class="top"><h1>Today</h1><span class="date">Tuesday</span></header>
                <div class="add" id="addRow"><span class="add-plus">+</span><span class="add-ph" id="addPh">Add a task</span><span class="add-in" id="addIn"></span></div>
                <div class="list" id="list">
                  <div class="row" id="row1"><span class="box"></span><span class="tx">Review the weekly plan</span><span class="when">9:00</span></div>
                  <div class="row" id="row2"><span class="box"></span><span class="tx">Send the invoice</span><span class="when">11:30</span></div>
                  <div class="row" id="row3"><span class="box"></span><span class="tx">Prepare the team update</span><span class="when">14:00</span></div>
                  <div class="row new" id="rowNew"><span class="box"></span><span class="tx" id="rowNewTx">{{TEXT_T1}}</span><span class="when">15:00</span></div>
                </div>
              </main>
              <div class="pvs-modal" id="pop1">
                <div class="pvs-backdrop"></div>
                <div class="pvs-box dlg">
                  <div class="dlg-h"><span>Send the invoice</span><span class="dlg-x" id="dlgClose">&#215;</span></div>
                  <div class="dlg-r"><span class="k">When</span><span>Today, 11:30</span></div>
                  <div class="dlg-r"><span class="k">Project</span><span>Billing</span></div>
                  <div class="dlg-r"><span class="k">Reminder</span><span>15 minutes before</span></div>
                </div>
              </div>
              <div class="pvs-toast-slot"><div class="pvs-toast toast" id="toast1">Task added to Today</div></div>
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
          <div class="pvs-mask"><div class="pvs-ln pvs-opS">{{POSITIONING}}</div></div>
        </div>
        <div class="pvs-ttl" id="tCh1"><div class="pvs-mask"><div class="pvs-ln pvs-chT">Plan <em>your day.</em></div></div></div>
        <div class="pvs-ttl" id="tCh2"><div class="pvs-mask"><div class="pvs-ln pvs-chT">Add <em>anything.</em></div></div></div>
        <div id="endS">
          <div class="pvs-end-bg"></div>
          <div class="pvs-end-content">
            <div class="pvs-eHead" id="eHead"><div class="pvs-mask"><div class="pvs-ln">One list, <em>planned for you.</em></div></div></div>
            <!-- each card names one capability from COVERAGE.md and carries a real UI piece -->
            <div class="pvs-cards">
              <div class="pvs-card" id="card1"><div class="pvs-card-h">Plans your day</div><div class="pvs-card-s">From what is due</div>
                <div class="pvs-card-ui"><div class="row mini"><span class="box"></span><span class="tx">Review the weekly plan</span></div></div></div>
              <div class="pvs-card" id="card2"><div class="pvs-card-h">Adds in a sentence</div><div class="pvs-card-s">Type it, it is scheduled</div>
                <div class="pvs-card-ui"><div class="row mini"><span class="box"></span><span class="tx">{{TEXT_T1}}</span></div></div></div>
              <div class="pvs-card" id="card3"><div class="pvs-card-h">Reminds you</div><div class="pvs-card-s">Before it is late</div>
                <div class="pvs-card-ui"><div class="toast mini">Reminder: Send the invoice</div></div></div>
            </div>
          </div>
        </div>
        <div id="lock">
          <img class="pvs-lkLogo" src="{{LOGO_ON_VEIL}}#lockup" alt="">
          <div class="pvs-lkT">{{PRODUCT_NAME}}</div>
          <div class="pvs-lkS">{{POSITIONING}}</div>
        </div>
        <div id="fade"></div>
      </div>

    {{AUDIO}}
    </div>

    <script>
      const T = (window.PVS_T = {{T_JSON}});
{{STAGE_JS}}

      PVS.ready((S) => {
        /* ---------- opening ---------- */
        S.fadeFromBlack(0.1);
        S.title("#tOpen", [T.open, T.open + 0.15, T.open + 0.6], T.ch1 - 0.05);

        /* ---------- chapter 1: plan your day (1x full page) ---------- */
        S.chapter("#tCh1", { at: T.ch1, rack: T.rack1, blurred: true });
        S.cursorShow(T.rack1 + 0.4);
        S.clickOn("#row2", T.open1, { hover: "hov", unhover: T.close1 + 0.3 });
        S.popupOpen("#pop1", T.open1);
        S.clickOn("#dlgClose", T.close1, { travel: 0.5 });
        S.popupClose("#pop1", T.close1);

        /* ---------- chapter 2: add anything (push-in planned in build.py, made behind the title) ---------- */
        S.chapter("#tCh2", { at: T.ch2, rack: T.rack2 });
        S.camPlan();
        S.clickOn("#addRow", T.inClick, { travel: 0.7 });
        S.state("#addRow", "foc", T.inClick);
        S.hide("#addPh", T.type1);
        S.type("#addIn", T.texts.t1, T.type1, T.type1Dur);
        S.hide("#addIn", T.add);
        S.show("#addPh", T.add, "inline");
        S.state("#addRow", null, T.add);
        S.show("#rowNew", T.add, "flex");
        S.fadeIn("#rowNew", T.add, 0.25, 6);
        S.toast("#toast1", T.add + 0.1, 1.8);

        /* ---------- end screen and lockup ---------- */
        S.cursorHide(T.endIn - 0.4);
        S.endScreen(T.endIn, { head: ["#eHead", T.endIn + 0.2], cards: [["#card1", T.card1], ["#card2", T.card2], ["#card3", T.card3]] });
        S.lockup(T.lockup);
        S.fadeToBlack(T.end);
      });
    </script>
  </body>
</html>
