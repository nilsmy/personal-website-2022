# AGENTS.md

## Site Purpose
- Personal academic/professional website for Nils Myszkowski (publications, R packages, teaching files, contact).
- Treat this as a production content site: preserve existing voice, structure, and visual style unless explicitly asked to redesign.

## Repository Structure
- `config.toml`: single Hugo config (no `config/_default/`, no `config.yaml`).
- `content/`: primary authored site content (home/about/blog/publications/R-packages/talk/form/license).
- `layouts/shortcodes/blogdown/postref.html`: local shortcode override used by blogdown-rendered pages.
- `assets/theme_1.scss`: active custom color theme.
- `static/`: downloadable files and images (CV, PDFs, datasets, homework, presentations, etc.).
- `themes/hugo-apero/`: vendored theme source (not Hugo Modules).
- `data/ads/formspree.yaml`: Formspree attribution data used by theme components.
- `R/`: `build.R` and `build2.R` placeholder hooks (currently comments only).
- `public/` and `resources/_gen/`: generated artifacts; avoid manual edits.

## Blogdown + Hugo Setup (Detected)
- Blogdown project marker: `index.Rmd` contains `site: blogdown:::blogdown_site`.
- Hugo theme configured in `config.toml` as `theme = "hugo-apero"`.
- Hugo version pinned to `0.84.4` in both:
  - `.Rprofile` (`options(blogdown.hugo.version = "0.84.4")`)
  - `netlify.toml` (`HUGO_VERSION = "0.84.4"`).
- Blogdown output mode in `.Rprofile`: `options(blogdown.method = 'html')`.
- `config.toml` ignores sources (`\\.Rmd$`, `\\.Rmarkdown$`, etc.), so rendered files are required for published content.

## Local Development Workflow
- Preferred:
  - `blogdown::serve_site()` for local preview.
  - Keep Hugo/blogdown versions aligned with the pinned Hugo `0.84.4`.
- Alternative: `hugo server` for quick checks (if content is already rendered).
- Before finishing: run a local build (`hugo`) when changes could affect templates, front matter, or routing.
- RStudio/blogdown rendering is required only when editing `index.Rmd` or `index.Rmarkdown` content that has committed rendered companions.
- For `.md`, front matter, layout, config, and style-only edits, knitting in RStudio is usually not required.

## Build and Deploy Workflow
- Netlify build config (`netlify.toml`):
  - Build command: `hugo`
  - Publish directory: `public`
  - Deploy previews/branch deploys: `hugo -F -b $DEPLOY_PRIME_URL`
  - Production env: `HUGO_ENV=production`
- Do not assume committed `public/` is authoritative for deploys; Netlify rebuilds from source.

## Netlify-Specific Constraints
- Do not change `netlify.toml` build command, publish dir, context commands, env vars, redirects, headers, forms, functions, or domain-related behavior unless explicitly asked.
- Be careful with absolute URLs and `baseURL`; current config uses `baseURL = "/"`.
- Preview deploys include future content via `-F`; do not “fix” this behavior unless requested.

## GitHub Workflow Expectations
- Git repo on `main` branch (no `.github/workflows/` detected in this repo).
- No in-repo CI guardrails: manually validate high-impact changes (build + spot-check relevant pages).
- Keep diffs focused and minimal; avoid bulk formatting or mass content churn.

## Editing Rules
- Prefer small, targeted edits over broad rewrites.
- Preserve current design system (hugo-apero + `assets/theme_1.scss`) unless redesign is requested.
- Reuse existing layouts/partials/shortcodes/content patterns before introducing new ones.
- Avoid adding dependencies/tooling (Node/R packages/build steps) unless clearly required.
- Do not edit generated files by hand unless task explicitly targets generated artifacts.

## Content Conventions
- Content is page-bundle oriented (`content/<section>/<slug>/index.*` + local assets).
- Front matter is YAML (`---`) and commonly includes:
  - `title`, `author`, `date`, `draft`, `excerpt`, `layout`, `categories`, `tags`, `links`.
- Personal-site byline convention: use `author: Nils Myszkowski` on publication pages (do not list full coauthor strings in page bylines).
- Publications and package pages use `links:` with icon metadata for PDF/CRAN links.
- Section-level behavior comes from `_index.md` cascade settings; preserve cascade semantics.

## Post and Page Conventions
- Mixed source types exist intentionally:
  - `index.md` (direct content)
  - `index.Rmd` / `index.Rmarkdown` (source)
  - paired rendered `index.html` / `index.markdown` (publishable)
- For R Markdown content updates, edit source and regenerate its paired rendered file; do not update only one side.
- Leave temporary lock files (`*.Rmd.lock~`) untouched unless explicitly cleaning content.

## Theme and Layout Conventions
- Minimal local override strategy is in use; only local custom layout found is:
  - `layouts/shortcodes/blogdown/postref.html`
- Prefer site-level overrides in `layouts/` over editing `themes/hugo-apero/`.
- Edit theme files only when no safer local override is possible and the task explicitly requires it.

## Assets and Static File Handling
- `static/` is for pass-through files served at site root paths; keep stable URL paths when replacing assets.
- `assets/` is Hugo pipeline input (SCSS/JS); keep changes compatible with Hugo 0.84.4.
- Avoid renaming/moving files referenced in front matter (`images`, `sharing_image`, PDF links) unless all references are updated.

## SEO / Metadata / Social Preview
- Preserve existing metadata behavior in `config.toml`:
  - `params.description`
  - `params.sharing_image`
  - taxonomies (`categories`, `series`, `tags`)
  - social links in `[[params.social]]`
- Preserve comments/analytics integrations unless task requires changes:
  - `params.utterances` (GitHub issue comments)
  - `googleAnalytics`/privacy settings
  - contact form behavior (`content/form/contact.md`, Formspree settings).

## Performance and Accessibility Expectations
- Keep pages responsive and maintain existing layouts (`list`, `list-grid`, `list-sidebar`, `single`, `split-right`).
- Avoid heavy new JS/CSS and large unoptimized media unless necessary.
- Keep meaningful alt text/captions and maintain heading structure in Markdown/R Markdown content.

## Safe Ways to Add Content
- New post/page:
  - Copy a nearby item in the same section as template.
  - Keep same front matter field patterns and layout keys.
  - Put related media in the same bundle folder.
- New publication/package entry:
  - Follow existing `links:` structure for PDF/CRAN buttons.
- New section:
  - Add `content/<section>/_index.md` with explicit layout/cascade.
  - Add menu entry in `config.toml` only if requested.

## Default PDF Intake Workflow
- Before creating a new publication entry, always run a duplicate check across existing `content/publications/` items using DOI, normalized title, slug, and PDF filename.
- If a likely match already exists, update the existing entry instead of creating a duplicate folder/page.
- If the user drops a paper PDF without extra instructions, default destination is `content/publications/<slug>/`.
- Default output to generate:
  - publication-style short abstract/excerpt in current site style
  - publication front matter (`title`, `author`, `date`, `excerpt`, `categories`, `tags`, `links`)
  - `links.url` pointing to the provided PDF path (typically under `static/Publication_pdf/`).
- Do not default these PDF entries to `content/blog/` unless explicitly requested.

## PDF Intake Implementation Notes (Repo-Verified)
- Sorting: publication listing order follows front matter date (newest first in current setup). Set `date` to publication date for correct placement.
- Build verification: use `Rscript -e "blogdown::build_site()"` if `hugo` is not available on shell PATH.
- Tooling fallback: `pdftotext`/`pdfinfo` are not installed in this environment; if needed, extract PDF metadata via `strings` for title/date/DOI/keywords.
- File placement: copy new paper PDFs to `static/Publication_pdf/` and link them from front matter `links.url`.

## Files to Avoid Changing Unless Necessary
- `netlify.toml`
- `config.toml` (especially menus, taxonomies, params, privacy/integration settings)
- `themes/hugo-apero/**`
- `public/**` and `resources/_gen/**` (generated)
- `.Rprofile` Hugo/blogdown version settings

## Fragile / High-Risk Areas
- Blogdown source/rendered pairing in `content/` (Rmd/Rmarkdown + html/markdown outputs).
- URL-sensitive links to static teaching/research files under `static/`.
- Contact/comments/social integrations (Formspree + utterances + social params).
- Theme compatibility with pinned Hugo 0.84.4.
