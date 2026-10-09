/* GrandStay — light animations: KPI count-up + animated progress bars.
   All effects degrade gracefully: if anything fails, the page still works. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. Count-up for KPI numbers (e.g. "$260", "20%", "1,234") ---------- */
  function animateNumbers() {
    if (reduceMotion) return;
    var nodes = document.querySelectorAll(".kpi-value");
    nodes.forEach(function (el) {
      var raw = el.textContent.trim();
      var m = raw.match(/^([^0-9\-]*)(-?[0-9][0-9.,]*)(.*)$/);
      if (!m) return;
      var prefix = m[1];
      var numText = m[2];
      var suffix = m[3];
      var target = parseFloat(numText.replace(/,/g, ""));
      if (!isFinite(target)) return;

      var decimals = (numText.split(".")[1] || "").length;
      var useGroup = numText.indexOf(",") !== -1 && decimals <= 2;
      var duration = 750;
      var start = null;

      function frame(now) {
        if (start === null) start = now;
        var p = Math.min((now - start) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        var value = target * eased;
        var text = value.toFixed(decimals);
        if (useGroup) {
          text = Number(text).toLocaleString("en-US", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
          });
        }
        el.textContent = prefix + text + suffix;
        if (p < 1) requestAnimationFrame(frame);
        else el.textContent = prefix + numText + suffix; // точне значення в кінці
      }
      requestAnimationFrame(frame);
    });
  }

  /* ---------- 2. Progress bars grow from 0 to their target width ---------- */
  function animateBars() {
    if (reduceMotion) return;
    document.querySelectorAll(".bar div").forEach(function (bar) {
      var target = bar.style.width;
      if (!target) return;
      bar.style.width = "0%";
      // force reflow so the transition actually runs
      void bar.offsetWidth;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          bar.style.width = target;
        });
      });
    });
  }

  /* ---------- 3. Subtle press feedback for buttons ---------- */
  function pressFeedback() {
    document.querySelectorAll(".btn").forEach(function (btn) {
      btn.addEventListener("pointerdown", function () {
        btn.style.transform = "translateY(0) scale(.97)";
      });
      ["pointerup", "pointerleave", "pointercancel"].forEach(function (ev) {
        btn.addEventListener(ev, function () {
          btn.style.transform = "";
        });
      });
    });
  }

  /* ---------- 4. Stay type: добір «Night / Day» на формі бронювання ----------
     У day-режимі (07:00 → 23:59) приховуємо поле виїзду та підставляємо
     йому дату заїзду: сервер сам ставить check_out = check_in, а значення
     поля потрібне, щоб міні-валідація cal.js не блокувала сабміт.
     Без JS все працює теж: поле виїзду видиме, користувач вводить ту саму
     дату — бізнес-логіка (день = 07:00 → 23:59) живе на сервері. */
  function initStayType() {
    Array.prototype.forEach.call(
      document.querySelectorAll('form select[name="stay_type"]'),
      function (sel) {
        var form = sel.closest("form");
        var checkIn = form && form.querySelector('input[name="check_in"]');
        var checkOut = form && form.querySelector('input[name="check_out"]');
        if (!form || !checkOut) return;
        function sync() {
          var day = sel.value === "Day";
          form.classList.toggle("day-mode", day);
          if (day && checkIn && checkIn.value) checkOut.value = checkIn.value;
        }
        sel.addEventListener("change", sync);
        if (checkIn) checkIn.addEventListener("change", sync);
        sync();
      }
    );
  }

  function init() {
    try { animateNumbers(); } catch (e) {}
    try { animateBars(); } catch (e) {}
    try { pressFeedback(); } catch (e) {}
    try { initStayType(); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
