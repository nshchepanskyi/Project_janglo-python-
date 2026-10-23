
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;


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
        var eased = 1 - Math.pow(1 - p, 3);
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
        else el.textContent = prefix + numText + suffix;
      }
      requestAnimationFrame(frame);
    });
  }


  function animateBars() {
    if (reduceMotion) return;
    document.querySelectorAll(".bar div").forEach(function (bar) {
      var target = bar.style.width;
      if (!target) return;
      bar.style.width = "0%";
      void bar.offsetWidth;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          bar.style.width = target;
        });
      });
    });
  }


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


  function initBurger() {
    var burger = document.querySelector(".p-burger");
    var nav = document.querySelector(".p-nav");
    if (!burger || !nav) return;
    document.documentElement.classList.add("burger-ready");

    var overlay = document.createElement("div");
    overlay.className = "nav-overlay";
    document.body.appendChild(overlay);

    function setOpen(open) {
      nav.classList.toggle("open", open);
      overlay.classList.toggle("show", open);
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      document.documentElement.classList.toggle("nav-locked", open);
    }

    burger.addEventListener("click", function () {
      setOpen(!nav.classList.contains("open"));
    });
    overlay.addEventListener("click", function () {
      setOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setOpen(false);
    });
    nav.addEventListener("click", function (e) {
      if (e.target && e.target.closest && e.target.closest("a")) setOpen(false);
    });
    if (window.matchMedia) {
      var mq = window.matchMedia("(max-width: 900px)");
      if (mq.addEventListener) {
        mq.addEventListener("change", function (ev) {
          if (!ev.matches) setOpen(false);
        });
      }
    }
  }

  function init() {
    try { animateNumbers(); } catch (e) {}
    try { animateBars(); } catch (e) {}
    try { pressFeedback(); } catch (e) {}
    try { initStayType(); } catch (e) {}
    try { initBurger(); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
