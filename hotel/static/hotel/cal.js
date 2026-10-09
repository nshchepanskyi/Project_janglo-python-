/* GrandStay — красивий діапазонний календар для полів дат
   (Check in / Check out) замість нативного браузерного пікера.

   Покращує <input type="date" class="js-cal">: перший клік — заїзд,
   другий — виїзд, між датами підсвічується діапазон ночей.
   Без JS поле залишається нативним (деградація без втрат).
   Мова береться з <html lang="..."> (en → USD-стиль, uk → українські
   назви місяців/днів і правила множини для «ночей»). */
(function () {
  "use strict";

  var html = document.documentElement;
  var LANG = (html.getAttribute("lang") || "en").toLowerCase().indexOf("uk") === 0 ? "uk" : "en";

  var STR = {
    en: {
      months: ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"],
      monthsShort: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
      dow: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
      weekStart: 0,
      choose: "Choose date",
      clear: "Clear",
      today: "Today",
      hintStart: "Select check-in date",
      hintEnd: "Select check-out date",
      prev: "Previous month",
      next: "Next month",
      nights: function (n) { return n === 1 ? "1 night" : n + " nights"; },
      title: function (y, m) { return this.months[m] + " " + y; },
      fmt: function (d) { return this.monthsShort[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear(); }
    },
    uk: {
      months: ["січень", "лютий", "березень", "квітень", "травень", "червень",
               "липень", "серпень", "вересень", "жовтень", "листопад", "грудень"],
      monthsGen: ["січня", "лютого", "березня", "квітня", "травня", "червня",
                  "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"],
      dow: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
      weekStart: 1,
      choose: "Оберіть дату",
      clear: "Очистити",
      today: "Сьогодні",
      hintStart: "Оберіть дату заїзду",
      hintEnd: "Оберіть дату виїзду",
      prev: "Попередній місяць",
      next: "Наступний місяць",
      nights: function (n) {
        var a = n % 10, b = n % 100;
        if (a === 1 && b !== 11) return n + " ніч";
        if (a >= 2 && a <= 4 && (b < 10 || b >= 20)) return n + " ночі";
        return n + " ночей";
      },
      title: function (y, m) { return this.months[m] + " " + y + " р."; },
      fmt: function (d) { return d.getDate() + " " + this.monthsGen[d.getMonth()] + " " + d.getFullYear() + " р."; }
    }
  }[LANG];

  var ICON =
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
    '<rect x="3" y="5" width="18" height="16" rx="3"></rect>' +
    '<path d="M8 3v4M16 3v4M3 10h18"></path></svg>';

  /* ---------- дати ---------- */
  var TODAY = new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());

  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function iso(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function parseISO(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  function ms(d) { return d.getTime(); }

  /* ---------- глобальний стан: відкритий календар ---------- */
  var openPop = null;
  var openTrigger = null;

  function closeAll() {
    if (openPop) openPop.hidden = true;
    openPop = null;
    openTrigger = null;
  }

  /* ---------- один календар на форму ---------- */
  function initForm(form) {
    var inputs = Array.prototype.slice.call(form.querySelectorAll("input[type=date].js-cal"));
    if (!inputs.length) return;

    form.classList.add("cal-host");

    var startInput = inputs[0];
    var endInput = inputs[1] || null;
    var st = { s: null, e: null, hover: null, vy: TODAY.getFullYear(), vm: TODAY.getMonth() };

    var pop = document.createElement("div");
    pop.className = "cal-pop";
    pop.hidden = true;
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", STR.choose);
    form.appendChild(pop);

    var triggers = inputs.map(function (inp) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cal-trigger";
      btn.innerHTML = '<span class="cal-text"></span><span class="cal-ico">' + ICON + "</span>";
      btn.setAttribute("aria-haspopup", "dialog");
      inp.insertAdjacentElement("afterend", btn);
      // обов'язковість переїжджає на кнопку (невидимий input не блокує сабміт)
      if (inp.required) {
        inp.setAttribute("data-required", "1");
        inp.required = false;
      }
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (openPop === pop && !pop.hidden) { closeAll(); return; }
        open(btn);
      });
      return btn;
    });

    function refresh() {
      inputs.forEach(function (inp, i) {
        var d = parseISO(inp.value);
        triggers[i].querySelector(".cal-text").textContent = d ? STR.fmt(d) : STR.choose;
        triggers[i].classList.toggle("has-value", !!d);
        triggers[i].classList.remove("cal-error");
      });
    }

    function commit() {
      startInput.value = st.s ? iso(st.s) : "";
      if (endInput) endInput.value = st.e ? iso(st.e) : "";
      inputs.forEach(function (inp) {
        inp.dispatchEvent(new Event("change", { bubbles: true }));
      });
      refresh();
    }

    function read() {
      st.s = parseISO(startInput.value);
      st.e = endInput ? parseISO(endInput.value) : null;
      if (st.s && st.e && st.e < st.s) { var t = st.s; st.s = st.e; st.e = t; }
      st.hover = null;
      var base = st.s || TODAY;
      st.vy = base.getFullYear();
      st.vm = base.getMonth();
    }

    function shift(delta) {
      var m = st.vm + delta, y = st.vy;
      if (m < 0) { m = 11; y--; } else if (m > 11) { m = 0; y++; }
      // не заглядаємо в минулі місяці
      if (y < TODAY.getFullYear() || (y === TODAY.getFullYear() && m < TODAY.getMonth())) return;
      st.vy = y; st.vm = m;
      render();
    }

    function pick(d) {
      if (d < TODAY) return;
      if (!endInput) { st.s = d; st.e = null; commit(); closeAll(); return; }
      if (!st.s || st.e || d <= st.s) {
        // новий вибір: перший клік завжди «заїзд»
        st.s = d;
        st.e = null;
        commit();
        render();
      } else {
        st.e = d;
        commit();
        closeAll();
      }
    }

    function render() {
      var y = st.vy, m = st.vm;
      var offset = (new Date(y, m, 1).getDay() - STR.weekStart + 7) % 7;
      var dim = new Date(y, m + 1, 0).getDate();
      var total = Math.ceil((offset + dim) / 7) * 7;

      var html_ = '<div class="cal-head">' +
        '<button type="button" class="cal-nav" data-nav="-1" aria-label="' + STR.prev + '"' +
          (y === TODAY.getFullYear() && m === TODAY.getMonth() ? " disabled" : "") + ">‹</button>" +
        '<div class="cal-title">' + STR.title(y, m) + "</div>" +
        '<button type="button" class="cal-nav" data-nav="1" aria-label="' + STR.next + '">›</button>' +
        "</div>" +
        '<div class="cal-grid">';

      for (var i = 0; i < 7; i++) html_ += '<div class="cal-dow">' + STR.dow[i] + "</div>";

      for (var j = 0; j < total; j++) {
        var d = new Date(y, m, 1 - offset + j);
        var past = d < TODAY;
        var cls = "cal-day";
        if (d.getMonth() !== m) cls += " is-out";
        if (past) cls += " is-past";
        html_ += '<button type="button" class="' + cls + '" data-t="' + ms(d) + '"' +
          (past ? " disabled" : "") + ">" + d.getDate() + "</button>";
      }

      html_ += "</div>" +
        '<div class="cal-foot"><span class="cal-hint"></span><span class="cal-actions">' +
        '<button type="button" class="cal-link" data-act="today">' + STR.today + "</button>" +
        '<button type="button" class="cal-link" data-act="clear">' + STR.clear + "</button>" +
        "</span></div>";

      pop.innerHTML = html_;
      paint();
    }

    function paint() {
      var s = st.s, e = st.e;
      var hi = e || ((!e && s) ? st.hover : null);

      Array.prototype.forEach.call(pop.querySelectorAll(".cal-day"), function (n) {
        var t = +n.getAttribute("data-t");
        n.classList.toggle("is-today", t === ms(TODAY));
        n.classList.toggle("is-sel-start", !!s && t === ms(s));
        n.classList.toggle("is-sel-end", !!e && t === ms(e));
        var inRange = !!(s && hi && t > ms(s) && t < ms(hi));
        n.classList.toggle("is-range", inRange);
        n.classList.toggle("is-preview", inRange && !e);
      });

      var hint = pop.querySelector(".cal-hint");
      if (hint) {
        if (s && e) hint.textContent = STR.nights(Math.round((e - s) / 86400000));
        else if (s) hint.textContent = STR.hintEnd;
        else hint.textContent = STR.hintStart;
      }
      var clear = pop.querySelector('[data-act="clear"]');
      if (clear) clear.disabled = !s && !e;
    }

    function position(btn) {
      if (window.innerWidth <= 560) { pop.style.top = ""; pop.style.left = ""; return; }
      var fr = form.getBoundingClientRect();
      var br = btn.getBoundingClientRect();
      var w = pop.offsetWidth, h = pop.offsetHeight;
      var top = br.bottom - fr.top + 8;
      if (br.bottom + h + 16 > window.innerHeight && br.top - h - 8 > fr.top) {
        top = br.top - fr.top - h - 8;
      }
      var left = br.left - fr.left;
      var max = form.clientWidth - w - 6;
      if (left > max) left = max;
      if (left < 6) left = 6;
      pop.style.top = top + "px";
      pop.style.left = left + "px";
    }

    function open(btn) {
      closeAll();
      read();
      render();
      pop.hidden = false;
      position(btn);
      openPop = pop;
      openTrigger = btn;
    }

    /* події всередині календаря */
    pop.addEventListener("click", function (ev) {
      var target = ev.target;
      var nav = target.closest && target.closest("[data-nav]");
      if (nav) { shift(+nav.getAttribute("data-nav")); return; }
      var act = target.closest && target.closest("[data-act]");
      if (act) {
        if (act.getAttribute("data-act") === "clear") {
          st.s = st.e = null;
          st.hover = null;
          commit();
          render();
        } else {
          st.vy = TODAY.getFullYear();
          st.vm = TODAY.getMonth();
          render();
        }
        return;
      }
      var day = target.closest && target.closest(".cal-day");
      if (day && !day.classList.contains("is-past")) pick(new Date(+day.getAttribute("data-t")));
    });

    pop.addEventListener("mouseover", function (ev) {
      if (!st.s || st.e) return;
      var day = ev.target.closest && ev.target.closest(".cal-day");
      if (!day) return;
      var d = new Date(+day.getAttribute("data-t"));
      if (d <= TODAY || d <= st.s) return;
      if (st.hover && ms(st.hover) === ms(d)) return;
      st.hover = d;
      paint();
    });

    pop.addEventListener("mouseleave", function () {
      if (st.hover) { st.hover = null; paint(); }
    });

    window.addEventListener("resize", function () {
      if (openPop === pop && !pop.hidden) position(openTrigger);
    });

    /* обов'язкові дати: підсвітимо кнопку, якщо користувач не обрав */
    form.addEventListener("submit", function (ev) {
      inputs.forEach(function (inp, i) {
        if (inp.getAttribute("data-required") && !inp.value) {
          ev.preventDefault();
          triggers[i].classList.add("cal-error");
          triggers[i].focus();
        }
      });
    });

    refresh();
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll("form"), initForm);
    html.classList.add("cal-ready");
  }

  /* закриття: клік поза календарем / Esc.
     Слухаємо capture-фазу: клік по дню фіксується ДО того, як render()
     перебудовує innerHTML і відʼєднує цільову кнопку. */
  document.addEventListener("click", function (ev) {
    if (!openPop) return;
    if (openPop.contains(ev.target) || (openTrigger && openTrigger.contains(ev.target))) return;
    closeAll();
  }, true);
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" || ev.keyCode === 27) closeAll();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
