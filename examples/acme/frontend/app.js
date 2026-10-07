/* Acme Tasks: a fictional to-do list that plans your day.
   Plain JavaScript, no build step. Serve the folder over http (icons and strings are fetched). */
(function () {
  "use strict";

  // Example tasks shown on first run (fictional data).
  const SEED_TASKS = [
    { title: "Confirm the cake order with Omar Haddad", time: "11:30 AM", project: "Orders" },
    { title: "Order flour for Saturday", time: "2:00 PM", project: "Supplies" },
    { title: "Bake the morning bread", time: "6:00 AM", project: "Kitchen" },
    { title: "Send the weekly invoices", time: "4:30 PM", project: "Office" },
  ];
  const TOAST_MS = 2400;

  let strings = {};
  let tasks = SEED_TASKS.map((t, i) => Object.assign({ id: i + 1 }, t));
  let planned = false;

  const $ = (sel) => document.querySelector(sel);
  const t = (key, vars) => {
    let s = strings[key] || key;
    Object.keys(vars || {}).forEach((k) => { s = s.replace("{" + k + "}", vars[k]); });
    return s;
  };

  // "6:00 AM" -> minutes after midnight; tasks without a time go last.
  function minutes(time) {
    const m = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec((time || "").trim());
    if (!m) return 24 * 60;
    let h = parseInt(m[1], 10) % 12;
    if (m[3].toUpperCase() === "PM") h += 12;
    return h * 60 + parseInt(m[2], 10);
  }
  const byTime = (a, b) => minutes(a.time) - minutes(b.time);

  async function loadStrings() {
    strings = await (await fetch("i18n/en.json")).json();
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  }

  async function loadIcons(root) {
    const els = (root || document).querySelectorAll("[data-icon]:empty");
    await Promise.all(Array.from(els).map(async (el) => {
      el.innerHTML = await (await fetch("icons/" + el.dataset.icon + ".svg")).text();
    }));
  }

  function rowHtml(task) {
    const project = task.project ? '<span class="task-project">' + task.project + "</span>" : "";
    return '<span class="task-check"></span><span class="task-title"></span>' + project +
      '<span class="task-time">' + (task.time || "") + "</span>";
  }

  function render(newId) {
    const list = $("#taskList");
    list.innerHTML = "";
    tasks.forEach((task) => {
      const li = document.createElement("li");
      li.className = "task" + (task.id === newId ? " is-new" : "");
      li.dataset.id = task.id;
      li.innerHTML = rowHtml(task);
      li.querySelector(".task-title").textContent = task.title;
      list.appendChild(li);
    });
    $("#taskCount").textContent = t("today.count", { count: tasks.length });
    $("#plannedChip").hidden = !planned;
    $("#emptyState").hidden = tasks.length > 0;
  }

  // Plan my day: order today's tasks by time. Rows slide to their new slot (FLIP).
  function planDay() {
    const before = {};
    document.querySelectorAll(".task").forEach((el) => { before[el.dataset.id] = el.getBoundingClientRect().top; });
    tasks.sort(byTime);
    planned = true;
    render();
    document.querySelectorAll(".task").forEach((el) => {
      const dy = (before[el.dataset.id] || 0) - el.getBoundingClientRect().top;
      if (!dy) return;
      el.style.transition = "none";
      el.style.transform = "translateY(" + dy + "px)";
      requestAnimationFrame(() => {
        el.style.transition = "";
        el.style.transform = "";
      });
    });
  }

  // A new task lands in its time slot once the day is planned, else at the end of the list.
  function addTask(title, time, project) {
    const task = { id: Date.now(), title: title, time: time, project: project };
    if (planned) {
      const at = tasks.findIndex((x) => byTime(task, x) < 0);
      tasks.splice(at < 0 ? tasks.length : at, 0, task);
    } else {
      tasks.push(task);
    }
    render(task.id);
    if (time) showToast(t("toast.added", { time: time }));
  }

  let toastTimer = 0;
  function showToast(text) {
    const el = $("#toast");
    el.textContent = text;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, TOAST_MS);
  }

  function openDialog() {
    $("#addForm").reset();
    $("#addDialog").hidden = false;
    $("#addForm").task.focus();
  }
  function closeDialog() { $("#addDialog").hidden = true; }

  function wire() {
    $("#planBtn").addEventListener("click", planDay);
    $("#addTaskBtn").addEventListener("click", openDialog);
    $("#addClose").addEventListener("click", closeDialog);
    $("#addCancel").addEventListener("click", closeDialog);
    $("#addDialog").addEventListener("click", (e) => { if (e.target === e.currentTarget) closeDialog(); });
    $("#addForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const f = e.currentTarget;
      addTask(f.task.value.trim(), f.time.value.trim(), f.project.value);
      closeDialog();
    });
    $("#todayDate").textContent = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await loadStrings();
    await loadIcons();
    wire();
    render();
  });
})();
