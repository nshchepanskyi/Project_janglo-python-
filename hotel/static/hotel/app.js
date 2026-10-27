
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

  function initBackgroundVideo() {
    if (reduceMotion) return;
    var theme = document.documentElement.getAttribute("data-theme") === "dark"
      ? "dark"
      : "light";
    var video = document.querySelector(".background-" + theme + "-video");
    if (!video) return;
    var source = video.getAttribute("data-src");
    if (!source) return;

    video.addEventListener("playing", function () {
      video.classList.add("is-playing");
    }, { once: true });
    video.src = source;
    video.load();
    var playback = video.play();
    if (playback && typeof playback.catch === "function") {
      playback.catch(function () {
        video.removeAttribute("src");
        video.load();
      });
    }
  }


  function initPasswordMatch() {
    document.querySelectorAll("[data-password-match-form]").forEach(function (form) {
      var firstName = form.getAttribute("data-match-first") || "password";
      var secondName = form.getAttribute("data-match-second") || "confirm";
      var first = form.querySelector('[name="' + firstName + '"]');
      var second = form.querySelector('[name="' + secondName + '"]');
      var error = form.querySelector(".inline-form-error");
      if (!first || !second || !error) return;

      function clearWhenMatching() {
        if (first.value === second.value) {
          error.hidden = true;
          second.removeAttribute("aria-invalid");
        }
      }

      first.addEventListener("input", clearWhenMatching);
      second.addEventListener("input", clearWhenMatching);
      form.addEventListener("submit", function (event) {
        if (first.value === second.value) {
          error.hidden = true;
          second.removeAttribute("aria-invalid");
          return;
        }
        event.preventDefault();
        error.hidden = false;
        second.setAttribute("aria-invalid", "true");
        second.focus();
      });
    });
  }


  function initProfileEditor() {
    var toggle = document.querySelector(".profile-edit-toggle");
    var panel = document.getElementById("profile-edit-panel");
    if (toggle && panel) {
      toggle.addEventListener("click", function () {
        var expanded = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
        panel.hidden = expanded;
      });
    }

    var avatarForm = document.querySelector("[data-profile-avatar-form]");
    if (!avatarForm) return;
    var fileInput = avatarForm.querySelector('input[type="file"]');
    var control = avatarForm.querySelector(".profile-avatar-control");
    var image = avatarForm.querySelector(".profile-avatar-image");
    var fallback = avatarForm.querySelector(".profile-avatar-fallback");
    var error = document.querySelector("[data-avatar-error]");
    if (!fileInput || !control || !image || !fallback || !error) return;

    control.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInput.click();
      }
    });

    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      if (!file) return;

      var oldSrc = image.getAttribute("src");
      var hadImage = !image.hidden && Boolean(oldSrc);
      var previewUrl = URL.createObjectURL(file);
      error.hidden = true;
      image.src = previewUrl;
      image.hidden = false;
      fallback.hidden = true;
      control.setAttribute("aria-busy", "true");

      var formAction = avatarForm.getAttribute("action") || window.location.href;
      fetch(formAction, {
        method: "POST",
        body: new FormData(avatarForm),
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      }).then(function (response) {
        if (!response.ok) throw new Error(error.getAttribute("data-upload-failed"));
        return response.text();
      }).then(function (html) {
        var parsed = new DOMParser().parseFromString(html, "text/html");
        var serverError = parsed.querySelector(".p-messages .msg.error");
        if (serverError) throw new Error(serverError.textContent.trim());
        var savedImage = parsed.querySelector(".profile-avatar-image[src]");
        if (savedImage) image.src = savedImage.getAttribute("src");
      }).catch(function (uploadError) {
        if (hadImage) {
          image.src = oldSrc;
          image.hidden = false;
          fallback.hidden = true;
        } else {
          image.removeAttribute("src");
          image.hidden = true;
          fallback.hidden = false;
        }
        error.textContent = uploadError.message || error.getAttribute("data-upload-failed");
        error.hidden = false;
      }).finally(function () {
        control.removeAttribute("aria-busy");
        fileInput.value = "";
        URL.revokeObjectURL(previewUrl);
      });
    });
  }

  function init() {
    try { animateNumbers(); } catch (e) {}
    try { animateBars(); } catch (e) {}
    try { pressFeedback(); } catch (e) {}
    initBackgroundVideo();
    try { initStayType(); } catch (e) {}
    try { initBurger(); } catch (e) {}
    try { initPasswordMatch(); } catch (e) {}
    try { initProfileEditor(); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
