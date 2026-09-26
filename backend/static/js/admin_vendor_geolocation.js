/**
 * "Get Location" button for the Vendor admin add/change form.
 *
 * Detects the visitor's approximate location from their IP address (via
 * ipapi.co — same service already used for the public-site location
 * modal, see templates/base.html) and matches it against our
 * Country → State → City data through the existing /ajax/location/
 * endpoint, then auto-selects the closest matching City in the "City"
 * dropdown. Falls back gracefully (asks the admin to pick manually) when
 * nothing matches or detection fails.
 *
 * Works with Unfold's Tom Select widgets (updates go through the Tom
 * Select API so the visible widget stays in sync) and plain <select>
 * elements alike.
 */
(function () {
  'use strict';

  var AJAX_URL = '/ajax/location/';
  var IPAPI_URL = 'https://ipapi.co/json/';

  function getTomSelect(el) {
    return el && el.tomselect ? el.tomselect : null;
  }

  function setCityValue(el, id) {
    var ts = getTomSelect(el);
    if (ts) {
      ts.setValue(String(id), true);
    } else {
      el.value = id;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function buildButton() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'vendor-get-location-btn';
    btn.innerHTML = '\uD83D\uDCCD Get Location';
    btn.style.cssText = [
      'margin-left:8px', 'white-space:nowrap', 'cursor:pointer',
      'padding:.5rem .9rem', 'font-size:.8125rem', 'font-weight:600',
      'border-radius:6px', 'border:1px solid #d0d5dd', 'background:#fff',
      'color:#344054',
    ].join(';');
    btn.addEventListener('mouseenter', function () { btn.style.background = '#f9fafb'; });
    btn.addEventListener('mouseleave', function () { btn.style.background = '#fff'; });
    return btn;
  }

  function buildStatus() {
    var span = document.createElement('span');
    span.id = 'vendor-get-location-status';
    span.style.cssText = 'margin-left:10px;font-size:.8125rem;';
    return span;
  }

  function init() {
    var cityEl = document.getElementById('id_city');
    if (!cityEl || document.getElementById('vendor-get-location-btn')) return;

    // Insert the button (and a status label) right after the city select's
    // own wrapper, so it sits inline beside the dropdown.
    var host = cityEl.closest('.related-widget-wrapper') || cityEl.parentElement;
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;margin-top:6px;';
    var btn = buildButton();
    var status = buildStatus();
    row.appendChild(btn);
    row.appendChild(status);
    host.parentElement.insertBefore(row, host.nextSibling);

    btn.addEventListener('click', function () {
      btn.disabled = true;
      status.style.color = '#667085';
      status.textContent = 'Detecting your location…';

      fetch(IPAPI_URL)
        .then(function (r) { return r.json(); })
        .then(function (geo) {
          var countryCode = geo.country_code || geo.country || '';
          var stateName = geo.region || '';
          var cityName = geo.city || '';
          if (!countryCode) throw new Error('no-country');

          var url = AJAX_URL + '?kind=match'
            + '&country_code=' + encodeURIComponent(countryCode)
            + '&state_name=' + encodeURIComponent(stateName)
            + '&city_name=' + encodeURIComponent(cityName);

          return fetch(url).then(function (r) { return r.json(); }).then(function (match) {
            if (match.city_id) {
              setCityValue(cityEl, match.city_id);
              status.style.color = '#067647';
              status.textContent = '\u2713 Detected: ' + match.city_name
                + (match.state_name ? ', ' + match.state_name : '');
            } else if (match.state_id) {
              status.style.color = '#b54708';
              status.textContent = 'Detected ' + match.state_name
                + ', but "' + cityName + '" isn\u2019t in our list yet \u2014 please pick a city manually.';
            } else {
              status.style.color = '#b54708';
              status.textContent = 'Couldn\u2019t match your location to a city \u2014 please select manually.';
            }
          });
        })
        .catch(function () {
          status.style.color = '#b54708';
          status.textContent = 'Location detection failed \u2014 please select manually.';
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();