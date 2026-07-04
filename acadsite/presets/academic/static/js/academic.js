// Progressive-enhancement interactions for the academic preset:
// mobile nav, expandable "see more" lists, and BibTeX show/copy.
(function () {
  // Mobile navigation
  document.addEventListener('click', function (e) {
    var toggle = e.target.closest('[data-mobile-toggle]');
    if (toggle) {
      var nav = document.querySelector('[data-mobile-nav]');
      if (!nav) return;
      var open = nav.hasAttribute('hidden');
      if (open) { nav.removeAttribute('hidden'); } else { nav.setAttribute('hidden', ''); }
      toggle.setAttribute('aria-expanded', String(open));
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
    if (expanded) { panel.setAttribute('hidden', ''); } else { panel.removeAttribute('hidden'); }
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
      pre.removeAttribute('hidden');
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
      pre.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();
