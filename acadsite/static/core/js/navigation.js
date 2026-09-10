// Progressive, same-origin page navigation for generated static sites.
// Direct URLs still render complete HTML documents; navbar clicks fetch the
// destination and swap only <main>, keeping the surrounding site shell alive.
(function () {
  'use strict';

  var main = document.querySelector('main#main');
  if (!main || !window.fetch || !window.DOMParser || !window.history) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var cache = new Map();
  var activeRequest = null;
  var navigationId = 0;
  var baseMeta = document.querySelector('meta[name="acadsite-base-path"]');
  var basePath = baseMeta ? baseMeta.content : '/';
  var navSelector = '.nav-link, .mobile-nav-link, .brand, .topnav-link, .wordmark';
  var status = document.createElement('span');
  status.className = 'navigation-status';
  status.setAttribute('aria-live', 'polite');
  status.setAttribute('aria-atomic', 'true');
  document.body.appendChild(status);

  function pageKey(url) {
    return url.pathname + url.search;
  }

  function isSitePage(url) {
    return url.origin === window.location.origin && url.pathname.indexOf(basePath) === 0;
  }

  function waitForExit() {
    if (reduceMotion.matches) return Promise.resolve();
    return new Promise(function (resolve) { window.setTimeout(resolve, 140); });
  }

  function nextFrame() {
    return new Promise(function (resolve) {
      window.requestAnimationFrame(function () { window.requestAnimationFrame(resolve); });
    });
  }

  function copyHead(nextDocument) {
    document.title = nextDocument.title;
    ['meta[name="description"]', 'meta[property="og:title"]', 'link[rel="canonical"]'].forEach(function (selector) {
      var current = document.head.querySelector(selector);
      var incoming = nextDocument.head.querySelector(selector);
      if (current && incoming) {
        Array.from(incoming.attributes).forEach(function (attribute) {
          current.setAttribute(attribute.name, attribute.value);
        });
      } else if (!current && incoming) {
        document.head.appendChild(incoming.cloneNode(true));
      } else if (current && !incoming) {
        current.remove();
      }
    });
  }

  function syncNavigation(nextDocument) {
    var incoming = Array.from(nextDocument.querySelectorAll(navSelector));
    document.querySelectorAll(navSelector).forEach(function (link) {
      var href = new URL(link.href, window.location.href);
      var match = incoming.find(function (candidate) {
        return pageKey(new URL(candidate.href, window.location.href)) === pageKey(href);
      });
      if (!match) return;
      link.className = match.className;
      if (match.hasAttribute('aria-current')) {
        link.setAttribute('aria-current', match.getAttribute('aria-current'));
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }

  function closeMobileNavigation() {
    var mobile = document.querySelector('[data-mobile-nav]');
    var toggle = document.querySelector('[data-mobile-toggle]');
    if (mobile) mobile.setAttribute('hidden', '');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  }

  function parsePage(html, responseUrl) {
    var parsed = new DOMParser().parseFromString(html, 'text/html');
    if (!parsed.querySelector('main#main')) throw new Error('Destination has no main content');
    var incomingBase = parsed.querySelector('meta[name="acadsite-base-path"]');
    if (!incomingBase || incomingBase.content !== basePath) {
      throw new Error('Destination is not an acadsite page for this site');
    }
    return { document: parsed, url: responseUrl };
  }

  function fetchPage(url) {
    var key = pageKey(url);
    if (cache.has(key)) return Promise.resolve(cache.get(key));
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();
    return fetch(url.href, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'acadsite-navigation' },
      signal: activeRequest.signal
    }).then(function (response) {
      if (!response.ok) throw new Error('Page request failed: ' + response.status);
      var finalUrl = new URL(response.url || url.href, window.location.href);
      if (!isSitePage(finalUrl)) throw new Error('Page request left this site');
      var contentType = response.headers.get('content-type') || '';
      if (contentType && contentType.indexOf('text/html') === -1) throw new Error('Destination is not HTML');
      return response.text().then(function (html) {
        var result = parsePage(html, finalUrl.href);
        cache.set(key, result);
        return result;
      });
    });
  }

  function scrollAfterNavigation(destination, savedScroll) {
    if (destination.hash) {
      var target = document.getElementById(decodeURIComponent(destination.hash.slice(1)));
      if (target) target.scrollIntoView();
      return;
    }
    window.scrollTo(0, typeof savedScroll === 'number' ? savedScroll : 0);
  }

  function navigate(destination, options) {
    options = options || {};
    var thisNavigation = ++navigationId;
    main.setAttribute('aria-busy', 'true');
    main.dataset.transitionState = 'leaving';

    return Promise.all([fetchPage(destination), waitForExit()]).then(function (values) {
      if (thisNavigation !== navigationId) return;
      var result = values[0];
      var nextDocument = result.document;
      var nextMain = nextDocument.querySelector('main#main');

      main.dataset.transitionState = 'entering';
      main.innerHTML = nextMain.innerHTML;
      copyHead(nextDocument);
      syncNavigation(nextDocument);
      closeMobileNavigation();

      if (options.push !== false) {
        history.replaceState({ scrollY: window.scrollY }, '', window.location.href);
        history.pushState({ scrollY: 0 }, '', destination.href);
      }
      scrollAfterNavigation(destination, options.scrollY);
      main.removeAttribute('aria-busy');

      return nextFrame().then(function () {
        main.removeAttribute('data-transition-state');
        status.textContent = document.title + ' loaded';
        document.dispatchEvent(new CustomEvent('acadsite:navigated', {
          detail: { url: destination.href, main: main }
        }));
        if (window.MathJax && window.MathJax.typesetPromise) window.MathJax.typesetPromise([main]);
      });
    }).catch(function (error) {
      if (error && error.name === 'AbortError') return;
      window.location.assign(destination.href);
    });
  }

  document.addEventListener('click', function (event) {
    var link = event.target.closest(navSelector);
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (link.hasAttribute('download') || (link.target && link.target !== '_self') || link.dataset.noPartialNavigation !== undefined) return;
    var destination = new URL(link.href, window.location.href);
    if (!isSitePage(destination)) return;
    if (pageKey(destination) === pageKey(new URL(window.location.href))) {
      event.preventDefault();
      scrollAfterNavigation(destination, 0);
      return;
    }
    event.preventDefault();
    navigate(destination);
  });

  window.addEventListener('popstate', function (event) {
    navigate(new URL(window.location.href), {
      push: false,
      scrollY: event.state && event.state.scrollY
    });
  });

  history.replaceState({ scrollY: window.scrollY }, '', window.location.href);
})();
