# How this project website was created

This document summarizes the steps taken to build the project website for the paper
**"Simple Disentanglement of Style and Content in Visual Representations"**
(Ngweta, Maity, Gittens, Sun, and Yurochkin — ICML 2023, PMLR vol. 202).

Source paper: https://proceedings.mlr.press/v202/ngweta23a/ngweta23a.pdf

## 1. Gathered information about the paper

- Fetched the PDF at the provided URL. The raw PDF binary couldn't be parsed directly for
  text, so it was downloaded as a side effect of the fetch.
- Fetched the paper's PMLR abstract page (`https://proceedings.mlr.press/v202/ngweta23a.html`)
  to get the title, full author list, abstract, publication venue/year, and links to the
  PDF and OpenReview forum.
- Fetched the OpenReview forum page (`https://openreview.net/forum?id=oupdxuURWD`) to
  confirm the verbatim abstract text and publication metadata (submission date, venue,
  decision).
- Fetched the BibTeX citation block embedded on the PMLR abstract page to get the exact,
  citable reference (cite key `pmlr-v202-ngweta23a`, including page numbers, editors,
  volume, and series).

## 2. Chose a location and structure for the site

- Confirmed with the user where to place the project and created the folder:
  `~/Downloads/SUNDAI/audio_thinker/`
- Created subfolders for static assets:
  - `assets/css/` — stylesheet
  - `assets/img/` — placeholder for any future figures/images from the paper

## 3. Built the website

A static, single-page HTML/CSS site (no build tools or frameworks needed) with the
following sections, modeled on the common "academic project page" layout used for ML
papers:

- **`index.html`**
  - Hero header: paper title, venue/year, full author list, and quick-link buttons to
    the PMLR abstract page, the PDF, OpenReview, and the on-page citation.
  - **Abstract** — the verbatim abstract text from the paper.
  - **Overview** — a plain-language summary of the paper's motivation (entangled
    style/content in pre-trained vision features), approach (a post-processing,
    probabilistic linear-entanglement model with a provable disentanglement algorithm),
    and results (improved domain generalization under style-driven distribution shift).
  - **Why it matters** — a short bulleted list of the paper's key selling points
    (scalability, theoretical guarantees, practical domain-generalization gains).
  - **BibTeX** — the exact citation block copied from the PMLR page, in a `<pre><code>`
    block for easy copy-pasting.
  - Footer with venue/page-number details and links back to PMLR and OpenReview.

- **`assets/css/style.css`**
  - Clean, responsive, single-column layout (max width ~860px) with a light hero
    section, pill-shaped link buttons, card-like code blocks for the BibTeX, and a
    mobile breakpoint that shrinks the title on narrow screens.

## 4. Verified the site

- Served the folder locally with `python3 -m http.server 8743` from inside
  `audio_thinker/`.
- Used `curl` to confirm `index.html` returns valid markup and `assets/css/style.css`
  returns `HTTP 200`.
- Opened the page in Safari (`open http://localhost:8743/index.html`) to visually confirm
  the layout renders as expected, then stopped the local server and removed temporary
  preview files.

## File listing

```
audio_thinker/
├── index.html              # the project page
├── SUMMARY.md              # this file
└── assets/
    ├── css/
    │   └── style.css       # page styling
    └── img/                # placeholder for future figures
```

## Possible next steps (not done here)

- Add figures/diagrams from the paper (e.g., the disentanglement method diagram or
  qualitative results) into `assets/img/` and reference them from the **Overview**
  section.
- Add a link to a code repository if/when one is published for the paper.
- Deploy the site (e.g., GitHub Pages, Netlify, or a personal domain) for public access.
