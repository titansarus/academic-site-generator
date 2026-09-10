// Progressive-enhancement interactions for the academic preset:
// mobile nav, expandable lists, and BibTeX show/copy.
(function () {
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
      { duration: opening ? 240 : 190, easing: 'cubic-bezier(.2,.8,.2,1)' }
    );
    animation.onfinish = function () {
      panel.style.removeProperty('overflow');
      delete panel.dataset.motionActive;
      if (done) done();
    };
  }

  // Mobile navigation
  document.addEventListener('click', function (e) {
    var toggle = e.target.closest('[data-mobile-toggle]');
    if (toggle) {
      var nav = document.querySelector('[data-mobile-nav]');
      if (!nav) return;
      var open = nav.hasAttribute('hidden');
      if (open) {
        animatePanel(nav, true);
      } else {
        animatePanel(nav, false, function () { nav.setAttribute('hidden', ''); });
      }
      toggle.setAttribute('aria-expanded', String(open));
    }
  });

  // Smooth native details panes while preserving no-JS disclosure behavior.
  document.addEventListener('click', function (e) {
    var summary = e.target.closest('.accordion-summary');
    if (!summary) return;
    var details = summary.closest('details');
    var content = details && details.querySelector('.accordion-content');
    if (!details || !content || content.dataset.motionActive === 'true') return;
    e.preventDefault();
    if (details.open) {
      animatePanel(content, false, function () { details.open = false; });
    } else {
      details.open = true;
      animatePanel(content, true);
    }
  });

  // Expandable "see more" sections
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-see-more]');
    if (!btn) return;
    var section = btn.closest('section') || document;
    var panel = section.querySelector('[data-collapsible]');
    if (!panel) return;
    var expanded = btn.getAttribute('aria-expanded') === 'true';
    if (expanded) {
      animatePanel(panel, false, function () { panel.setAttribute('hidden', ''); });
    } else {
      animatePanel(panel, true);
    }
    btn.setAttribute('aria-expanded', String(!expanded));
    var label = btn.querySelector('[data-see-more-label]');
    if (label) label.textContent = expanded ? 'Show more' : 'Show less';
  });

  // BibTeX: toggle visibility and copy to clipboard
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-bibtex-toggle]');
    if (!btn) return;
    var item = btn.closest('.pub-item');
    if (!item) return;
    var pre = item.querySelector('[data-bibtex]');
    if (!pre) return;
    var hidden = pre.hasAttribute('hidden');
    if (hidden) {
      animatePanel(pre, true);
      btn.setAttribute('aria-expanded', 'true');
      var text = pre.textContent;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () {
          var prev = btn.textContent;
          btn.textContent = 'Copied!';
          setTimeout(function () { btn.textContent = prev; }, 1400);
        }).catch(function () {});
      }
    } else {
      animatePanel(pre, false, function () { pre.setAttribute('hidden', ''); });
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();
