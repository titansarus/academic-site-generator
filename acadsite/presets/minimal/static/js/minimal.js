// Theme2 interactions: light/dark toggle and BibTeX show/copy.
(function () {
  var root = document.documentElement;
  var KEY = 'acadsite-theme';
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function animatePanel(panel, opening, done) {
    if (!panel || panel.dataset.motionActive === 'true') return;
    if (opening) panel.removeAttribute('hidden');
    if (reduceMotion.matches || !panel.animate) {
      if (done) done();
      return;
    }
    panel.dataset.motionActive = 'true';
    var height = panel.scrollHeight;
    panel.style.overflow = 'hidden';
    var animation = panel.animate(
      opening
        ? [{ height: '0px', opacity: 0 }, { height: height + 'px', opacity: 1 }]
        : [{ height: height + 'px', opacity: 1 }, { height: '0px', opacity: 0 }],
      { duration: opening ? 230 : 180, easing: 'cubic-bezier(.2,.8,.2,1)' }
    );
    animation.onfinish = function () {
      panel.style.removeProperty('overflow');
      delete panel.dataset.motionActive;
      if (done) done();
    };
  }

  function current() { return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }

  function syncLabel() {
    var isDark = current() === 'dark';
    document.querySelectorAll('[data-theme-label]').forEach(function (el) {
      el.textContent = isDark ? '☀' : '☾';
    });
    document.querySelectorAll('[data-theme-toggle]').forEach(function (el) {
      el.setAttribute('aria-pressed', String(isDark));
      el.setAttribute('title', isDark ? 'Switch to light' : 'Switch to dark');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (btn) {
      e.preventDefault();
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem(KEY, next); } catch (err) {}
      syncLabel();
    }
  });

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-bibtex-toggle]');
    if (!btn) return;
    var li = btn.closest('li');
    var pre = li && li.querySelector('[data-bibtex]');
    if (!pre) return;
    if (pre.hasAttribute('hidden')) {
      animatePanel(pre, true);
      btn.setAttribute('aria-expanded', 'true');
      if (navigator.clipboard) {
        navigator.clipboard.writeText(pre.textContent).then(function () {
          var prev = btn.textContent;
          btn.textContent = 'copied!';
          setTimeout(function () { btn.textContent = prev; }, 1300);
        }).catch(function () {});
      }
    } else {
      animatePanel(pre, false, function () { pre.setAttribute('hidden', ''); });
      btn.setAttribute('aria-expanded', 'false');
    }
  });

  syncLabel();
})();
