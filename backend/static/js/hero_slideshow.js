/**
 * Home page hero background slideshow.
 *
 * Shows one hero background image at a time and crossfades to the next.
 * Images themselves come from the server (either admin-uploaded
 * HomeBackgroundImage records, or the static fallback images) — this script
 * only handles the timing/transition, so no build step is needed for admins
 * to change what's shown; they just upload a new image in the admin.
 */
(function () {
  var SLIDE_DURATION_MS = 4000; // how long each image stays fully visible

  function initHeroSlideshow() {
    var slides = document.querySelectorAll('.hero-slides .hero-slide-fade');
    if (slides.length <= 1) return; // nothing to rotate

    var prefersReducedMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return; // respect user preference, keep first image static

    var current = 0;
    var timer = null;
    var heroEl = document.querySelector('.hero');

    function goToNext() {
      var next = (current + 1) % slides.length;
      slides[current].classList.remove('is-active');
      slides[next].classList.add('is-active');
      current = next;
    }

    function start() {
      if (timer) return;
      timer = window.setInterval(goToNext, SLIDE_DURATION_MS);
    }

    function stop() {
      if (!timer) return;
      window.clearInterval(timer);
      timer = null;
    }

    start();

    // Pause on hover/focus so users can read text over the hero without it
    // changing under them, matching the previous slideshow's behaviour.
    if (heroEl) {
      heroEl.addEventListener('mouseenter', stop);
      heroEl.addEventListener('mouseleave', start);
    }

    // Pause when the tab isn't visible to avoid a burst of transitions
    // firing when the user comes back.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeroSlideshow);
  } else {
    initHeroSlideshow();
  }
})();