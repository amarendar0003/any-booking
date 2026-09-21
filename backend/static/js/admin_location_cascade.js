/**
 * Cascading country → state → city dropdowns for the StaffProfile admin forms.
 *
 * Works with Unfold's Tom Select widgets: updates are applied via the
 * Tom Select API (element.tomselect) so the visible widget stays in sync.
 * Falls back to plain <select> manipulation when Tom Select isn't present.
 */
(function () {
  'use strict';

  var AJAX_URL = '/ajax/location/';

  /* ------------------------------------------------------------------
   * Tom Select helpers
   * ------------------------------------------------------------------ */
  function getTomSelect(el) {
    return el && el.tomselect ? el.tomselect : null;
  }

  function setOptions(el, options, keepValue) {
    var ts = getTomSelect(el);
    var current = keepValue ? el.value : '';
    if (ts) {
      ts.clear(true);
      ts.clearOptions();
      ts.addOption({ value: '', text: '---------' });
      options.forEach(function (o) {
        ts.addOption({ value: String(o.id), text: o.name });
      });
      ts.refreshOptions(false);
      if (current && options.some(function (o) { return String(o.id) === current; })) {
        ts.setValue(current, true);
      } else {
        ts.setValue('', true);
      }
    } else {
      var saved = current;
      el.innerHTML = '<option value="">---------</option>';
      options.forEach(function (o) {
        var opt = document.createElement('option');
        opt.value = o.id;
        opt.text = o.name;
        el.appendChild(opt);
      });
      el.value = saved || '';
    }
  }

  function clearField(el) {
    setOptions(el, [], false);
  }

  /* ------------------------------------------------------------------
   * Fetch helpers
   * ------------------------------------------------------------------ */
  function fetchStates(countryId, cb) {
    fetch(AJAX_URL + '?kind=states&parent_id=' + countryId)
      .then(function (r) { return r.json(); })
      .then(function (d) { cb(d.results || []); });
  }

  function fetchCities(stateId, cb) {
    fetch(AJAX_URL + '?kind=cities_by_state&parent_id=' + stateId)
      .then(function (r) { return r.json(); })
      .then(function (d) { cb(d.results || []); });
  }

  /* ------------------------------------------------------------------
   * Bind one country/state/city triple
   * ------------------------------------------------------------------ */
  function bindTriple(countryEl, stateEl, cityEl) {
    /* Country → State */
    countryEl.addEventListener('change', function () {
      clearField(stateEl);
      clearField(cityEl);
      if (this.value) {
        fetchStates(this.value, function (states) {
          setOptions(stateEl, states, false);
        });
      }
    });

    /* State → City */
    stateEl.addEventListener('change', function () {
      clearField(cityEl);
      if (this.value) {
        fetchCities(this.value, function (cities) {
          setOptions(cityEl, cities, false);
        });
      }
    });

    /* On page load with existing values: re-filter to match stored selection */
    var initCountry = countryEl.value;
    var initState   = stateEl.value;
    var initCity    = cityEl.value;

    if (initCountry) {
      fetchStates(initCountry, function (states) {
        setOptions(stateEl, states, false);
        /* restore the saved state value after re-populating */
        var ts = getTomSelect(stateEl);
        if (ts) {
          ts.setValue(initState, true);
        } else {
          stateEl.value = initState;
        }

        if (initState) {
          fetchCities(initState, function (cities) {
            setOptions(cityEl, cities, false);
            var tsc = getTomSelect(cityEl);
            if (tsc) {
              tsc.setValue(initCity, true);
            } else {
              cityEl.value = initCity;
            }
          });
        }
      });
    }
  }

  /* ------------------------------------------------------------------
   * Find and wire all triples on the page
   * ------------------------------------------------------------------ */
  function init() {
    /* Match both standalone admin (id_country) and inline variants
     * (id_staff_profile-0-country, id_staff_profile-__prefix__-country …) */
    var countryFields = document.querySelectorAll(
      'select[id="id_country"], select[id$="-country"]'
    );

    countryFields.forEach(function (countryEl) {
      var prefix = countryEl.id.replace(/country$/, '');
      var stateEl = document.getElementById(prefix + 'state');
      var cityEl  = document.getElementById(prefix + 'city');
      if (stateEl && cityEl) {
        bindTriple(countryEl, stateEl, cityEl);
      }
    });
  }

  /* Run after Unfold has had a chance to initialise Tom Select widgets */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
