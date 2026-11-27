// Shared helpers for the 100-project series.
// - Delete confirmations: add data-confirm="Are you sure?" to a button/link.
// - Copy to clipboard: add data-copy="text to copy" to a button.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (ev) {
      if (!window.confirm(el.getAttribute("data-confirm"))) {
        ev.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-copy]").forEach(function (el) {
    el.addEventListener("click", function () {
      var text = el.getAttribute("data-copy");
      var original = el.textContent;
      function done() {
        el.textContent = "Copied!";
        setTimeout(function () { el.textContent = original; }, 1500);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {
          fallbackCopy(text);
          done();
        });
      } else {
        fallbackCopy(text);
        done();
      }
    });
  });

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* ignore */ }
    document.body.removeChild(ta);
  }

  // Flash messages disappear after 5 seconds.
  setTimeout(function () {
    document.querySelectorAll(".flash").forEach(function (f) { f.remove(); });
  }, 5000);
});
