# How Category Images Work — "Browse by Category" (Home Page)

This file explains exactly how the images shown on the home page's
**Browse by Category** scrolling cards are found, chosen, and displayed.

---

## 1. The three pieces involved

| # | File / Folder | Role |
|---|---------------|------|
| 1 | `backend/templates/home.html` (lines ~92–150) | The card markup — decides WHAT to show |
| 2 | `backend/services/models.py` → `Category.static_image_url` property (lines ~139–155) | Builds the image PATH automatically |
| 3 | `backend/static/img/` folder | Holds the actual image FILES |

No other file in the project is involved in category card images.

---

## 2. The flow (step by step)

When the home page renders, for EACH category card:

```
Template (home.html):
    {% if cat.static_image_url %}          ← step A: does a static image exist?
        <img src="{% static cat.static_image_url %}">   ← show the photo
    {% else %}                              ← step B: no image found
        <div class="cat-tile-bg">🏛️</div>   ← orange background + emoji fallback
    {% endif %}
```

Step A — what `static_image_url` (models.py) does:

    1. Takes the category's slug (e.g. 'banquet_hall')
    2. Builds candidate paths:   img/banquet_hall.png
                                 img/banquet_hall.jpg
                                 img/banquet_hall.jpeg
                                 img/banquet_hall.webp
    3. Returns the FIRST one that actually exists in the static folders
    4. If none exist → returns None → template shows the emoji fallback

Step B — the emoji fallback also comes from home.html:

    {% if cat.slug == 'banquet_hall' %}🏛️
    {% elif cat.slug == 'music_band' %}🎸
    {% elif cat.slug == 'catering' %}🍽️
    {% elif cat.slug == 'hotels' %}🏨
    {% elif cat.slug == 'dancing' %}💃
    {% elif cat.slug == 'priests' %}🪔
    {% elif cat.slug == 'event_management' %}🎪
    {% else %} <Bootstrap icon from cat.icon> {% endif %}

---

## 3. The naming rule (the ONLY rule)

    image filename  =  category slug  +  .png / .jpg / .jpeg / .webp

Current mapping (all files live in `backend/static/img/`):

    Category name      slug                image file
    -------------      ----                ----------
    Banquet Hall       banquet_hall        banquet_hall.png
    Music Band         music_band          music_band.png
    Catering           catering            catering.png
    Hotels             hotels              hotels.png
    Dancing            dancing             dancing.png
    Priests            priests             priests.png
    Event Management   event_management    event_management.png

Because the path is built from the slug, EVERY category — including
new ones added later — is covered automatically. No code edits needed.

---

## 4. Common tasks

### Change a card's image
Overwrite the file in `backend/static/img/` (keep the same name).
E.g. replace `hotels.png` with a new photo → done.

### Add an image for a NEW category
1. Add the category in the admin and note its slug, e.g. `photography`
2. Save your photo as `photography.png` in `backend/static/img/`
3. Refresh the page — the card picks it up automatically
4. Until you add the file, the card shows its emoji (never a broken image)

### Change image WITHOUT following the naming rule
Two options:

a) **Rename your file** to match the slug (recommended, zero code changes)

b) **Hardcode it in the template** — in `backend/templates/home.html`,
   replace the `{% if cat.static_image_url %}` check with an explicit
   slug check:

       {% if cat.slug == 'hotels' %}
         <img class="cat-tile-img" src="{% static 'img/my_photo.jpg' %}">
       {% elif cat.static_image_url %}
         <img class="cat-tile-img" src="{% static cat.static_image_url %}">
       {% else %}
         ... emoji fallback ...
       {% endif %}

   Here `my_photo.jpg` can have ANY name. Do this in BOTH card loops
   (the original loop AND the `data-clone` marquee loop) so the
   scrolling animation stays consistent.
   NOTE: if the file does not exist, the browser shows a broken image —
   that's why option (a) is safer.

### Alternative: admin-uploaded image (not currently wired)
The Category model already has a field for this:

    image = models.ImageField(upload_to='categories/', blank=True)

Uploading via Django admin would give per-category images with any
filename, but the home page template does not read this field yet.
To activate it, `home.html` would check `cat.image` FIRST, before
`static_image_url`. (Not needed while the static-folder method works.)

---

## 5. Related but separate

- `main.css` (.cat-tile, .cat-tile-media, .cat-tile-img, .cat-tile-info)
  controls the card's SIZE and LAYOUT (300px tall, image on top,
  text strip at bottom) — not which image is shown.
- The card text ("Banquet Hall", "5 listings") also comes from
  home.html, not from the image logic.
