#!/usr/bin/env python3
"""Create SEO pages for newly added public recipes without overwriting curated pages."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import html, json, os, re, sys, xml.etree.ElementTree as ET

BASE = "https://chidseychowdown.co.uk"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vjqffpdggasgtgnxtktj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_YyUFvcXzXzDjI3tZX8P7kg_SyNSWUJK")
BOOK_KEY = "chris"
ROOT = Path(".")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}

def get_public_book():
    query = urlencode({"select": "data,updated_at", "book_key": "eq." + BOOK_KEY, "limit": "1"})
    req = Request(SUPABASE_URL + "/rest/v1/public_recipe_books?" + query, headers=HEADERS)
    with urlopen(req, timeout=25) as response:
        rows = json.loads(response.read().decode("utf-8"))
    if not rows or not isinstance(rows[0].get("data"), dict):
        raise RuntimeError("The public recipe book could not be read. No files were changed.")
    return rows[0]["data"]

def slugify(value):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "recipe"

def esc(value):
    return html.escape(str(value or "").strip(), quote=True)

def duration_iso(value):
    """Convert an explicitly stored duration into Schema.org ISO 8601."""
    if value is None or value == "":
        return ""
    text = str(value).lower()
    matches = re.findall(r"(\d+)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", text)
    if not matches:
        return ""
    minutes = 0
    for amount, unit in matches:
        n = int(amount)
        minutes += n * 60 if unit.startswith("h") else n
    if len(matches) == 2 and re.search(r"\d+\s*[–-]\s*\d+", text):
        minutes = max(int(matches[0][0]) * (60 if matches[0][1].startswith("h") else 1),
                      int(matches[1][0]) * (60 if matches[1][1].startswith("h") else 1))
    return f"PT{minutes}M" if minutes > 0 else ""


def lines(value):
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"\r?\n|\s*;\s*", str(value or ""))
    return [str(x).strip(" •\t-") for x in raw if str(x).strip(" •\t-")]

def recipe_page(recipe, slug):
    name = str(recipe.get("name") or "Recipe").strip()
    desc = str(recipe.get("description") or ("A homemade recipe from The Chidsey Chowdown: " + name + ".")).strip()
    ingredients = lines(recipe.get("ingredients"))
    method = lines(recipe.get("method") or recipe.get("instructions"))
    if not ingredients or not method:
        return None
    categories = recipe.get("categories") or [recipe.get("category") or "Recipes"]
    if not isinstance(categories, list):
        categories = [categories]
    url = f"{BASE}/recipes/{slug}/"
    image = str(recipe.get("photo") or "")
    if image and not image.startswith(("https://", "http://")):
        image = BASE + "/" + image.lstrip("/")
    data = {
        "@context": "https://schema.org", "@type": "Recipe", "name": name,
        "description": desc, "author": {"@type": "Person", "name": "Chris"},
        "mainEntityOfPage": url, "url": url, "recipeCategory": categories,
        "recipeIngredient": ingredients,
        "recipeInstructions": [{"@type": "HowToStep", "position": i+1, "name": f"Step {i+1}", "text": x} for i, x in enumerate(method)]
    }
    total_time = duration_iso(recipe.get("time"))
    if total_time:
        data["totalTime"] = total_time
    prep_time = duration_iso(recipe.get("prepTime") or recipe.get("prep_time"))
    cook_time = duration_iso(recipe.get("cookTime") or recipe.get("cook_time"))
    if prep_time:
        data["prepTime"] = prep_time
    if cook_time:
        data["cookTime"] = cook_time
    cuisine = recipe.get("recipeCuisine") or recipe.get("cuisine")
    if cuisine:
        data["recipeCuisine"] = cuisine
    if image:
        data["image"] = [image]
    title = esc(name + " | The Chidsey Chowdown")
    parts = [
      '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
      f'<title>{title}</title><meta name="description" content="{esc(desc[:300])}"><meta name="robots" content="index,follow,max-image-preview:large">',
      f'<link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:site_name" content="The Chidsey Chowdown"><meta property="og:title" content="{title}"><meta property="og:description" content="{esc(desc[:300])}"><meta property="og:url" content="{url}">',
      '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + '</script>',
      '<style>:root{color-scheme:light;--green:#49634c;--ink:#263238;--muted:#5f6b76;--line:#dfe7e1;--pale:#f3f7f4}*{box-sizing:border-box}body{margin:0;background:#f5f7f5;color:var(--ink);font:17px/1.65 system-ui,-apple-system,sans-serif}header{background:var(--green);color:white;padding:22px max(20px,calc((100% - 900px)/2))}header a{color:white;text-decoration:none;font-weight:700}main{max-width:900px;margin:28px auto;padding:0 20px 48px}.card{background:white;border:1px solid var(--line);border-radius:18px;padding:clamp(22px,4vw,42px)}h1{font-size:clamp(2rem,5vw,3rem);line-height:1.15;margin:0 0 12px;letter-spacing:-.04em}.desc{color:var(--muted);font-size:1.1rem}.recipe-image{display:block;max-width:100%;height:auto;max-height:480px;object-fit:cover;border-radius:12px;margin:22px auto}h2{margin-top:30px;color:var(--green)}li{margin:.4em 0}.back{display:inline-block;margin-top:24px;padding:10px 16px;background:var(--green);color:white;text-decoration:none;border-radius:9px}</style></head><body>',
      '<header><a href="/">The Chidsey Chowdown</a></header><main><article class="card">',
      f'<h1>{esc(name)}</h1><p class="desc">{esc(desc)}</p>'
    ]
    if image:
        parts.insert(3, f'<meta property="og:image" content="{esc(image)}"><meta property="og:image:alt" content="{esc(name)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{esc(image)}">')
    if image:
        parts.append(f'<img class="recipe-image" src="{esc(image)}" alt="{esc(name)}">')
    parts.append('<h2>Ingredients</h2><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in ingredients) + '</ul>')
    parts.append('<h2>Method</h2><ol>' + ''.join(f'<li>{esc(x)}</li>' for x in method) + '</ol>')
    parts.append(f'<a class="back" href="/?recipe={esc(recipe.get("id",""))}">View this recipe in the recipe book</a></article></main></body></html>')
    return ''.join(parts)

def refresh_existing_recipe_metadata(target, recipe):
    """Refresh photo metadata on an existing SEO page without rebuilding its curated content."""
    image = str(recipe.get("photo") or "").strip()
    if image and not image.startswith(("https://", "http://")):
        image = BASE + "/" + image.lstrip("/")
    source = target.read_text(encoding="utf-8")
    updated = source

    # Keep social previews in step with the current public recipe photo.
    def set_meta(source, attribute, key, content):
        pattern = re.compile(
            r'<meta\s+' + re.escape(attribute) + r'="' + re.escape(key) + r'"\s+content="[^"]*"\s*/?>',
            re.I
        )
        tag = f'<meta {attribute}="{key}" content="{esc(content)}">'
        if pattern.search(source):
            return pattern.sub(lambda _: tag, source, count=1)
        return re.sub(r'</head>', tag + '</head>', source, count=1, flags=re.I)

    if image:
        updated = set_meta(updated, "property", "og:image", image)
        updated = set_meta(updated, "name", "twitter:image", image)
        updated = set_meta(updated, "property", "og:image:alt", recipe.get("name") or "Recipe")

    # Update the Recipe JSON-LD image used by search engines.
    script_pattern = re.compile(
        r'(<script\s+type="application/ld\+json"\s*>)(.*?)(</script>)',
        re.I | re.S
    )
    match = script_pattern.search(updated)
    if match:
        try:
            schema = json.loads(match.group(2))
            if isinstance(schema, dict) and schema.get("@type") == "Recipe":
                if image:
                    schema["image"] = [image]
                recipe_url = f"{BASE}/recipes/{target.parent.name}/"
                schema["url"] = recipe_url
                schema["mainEntityOfPage"] = recipe_url
                total_time = duration_iso(recipe.get("time"))
                if total_time:
                    schema["totalTime"] = total_time
                prep_time = duration_iso(recipe.get("prepTime") or recipe.get("prep_time"))
                cook_time = duration_iso(recipe.get("cookTime") or recipe.get("cook_time"))
                if prep_time:
                    schema["prepTime"] = prep_time
                if cook_time:
                    schema["cookTime"] = cook_time
                cuisine = recipe.get("recipeCuisine") or recipe.get("cuisine")
                if cuisine:
                    schema["recipeCuisine"] = cuisine
                steps = schema.get("recipeInstructions")
                if isinstance(steps, list):
                    for index, step in enumerate(steps):
                        if isinstance(step, dict) and step.get("@type") == "HowToStep" and not step.get("name"):
                            step["name"] = f"Step {index + 1}"
                replacement = match.group(1) + json.dumps(
                    schema, ensure_ascii=False
                ).replace("</", "<\\/") + match.group(3)
                updated = updated[:match.start()] + replacement + updated[match.end():]
        except (ValueError, TypeError):
            pass

    # Ensure the recipe page visibly displays the same photograph when one exists.
    if image:
        img_tag = f'<img class="recipe-image" src="{esc(image)}" alt="{esc(recipe.get("name") or "Recipe")}">'
        existing_img = re.compile(r'<img\b[^>]*class="[^"]*\brecipe-image\b[^"]*"[^>]*>', re.I)
        if existing_img.search(updated):
            updated = existing_img.sub(lambda _: img_tag, updated, count=1)
        else:
            desc = re.compile(r'(<p\s+class="desc">.*?</p>)', re.I | re.S)
            if desc.search(updated):
                updated = desc.sub(lambda m: m.group(1) + img_tag, updated, count=1)

    if updated != source:
        target.write_text(updated, encoding="utf-8")
        return True
    return False


def main():
    book = get_public_book()
    recipes = book.get("recipes", [])
    if not isinstance(recipes, list):
        raise RuntimeError("Unexpected recipe data format. No files were changed.")
    deleted = set(str(x) for x in book.get("deletedIds", []))
    generated = []
    reserved = set()
    for r in recipes:
        if not isinstance(r, dict) or not r.get("id") or str(r["id"]) in deleted:
            continue
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        base = slugify(name)
        slug = base
        if slug in reserved:
            slug = base + "-" + slugify(str(r["id"]))
        reserved.add(slug)
        folder = ROOT / "recipes" / slug
        target = folder / "index.html"
        # Never replace existing hand-reviewed pages; only create pages for new recipes.
        if target.exists():
            if refresh_existing_recipe_metadata(target, r):
                print(f"Refreshed recipe photo metadata: {name}")
            continue
        page = recipe_page(r, slug)
        if not page:
            print(f"Skipping {name}: ingredients or method are missing.")
            continue
        folder.mkdir(parents=True, exist_ok=True)
        target.write_text(page + "\n", encoding="utf-8")
        generated.append((slug, name))
    sitemap = ROOT / "sitemap.xml"
    tree = ET.parse(sitemap)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    existing = {el.text for el in root.findall("sm:url/sm:loc", ns)}
    today = __import__("datetime").date.today().isoformat()
    for slug, _ in generated:
        url = f"{BASE}/recipes/{slug}/"
        if url in existing:
            continue
        node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = url
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = today
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq").text = "monthly"
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}priority").text = "0.7"
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    print(f"Created {len(generated)} new SEO page(s); existing reviewed pages were left unchanged.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("SEO generation failed safely:", str(e), file=sys.stderr)
        raise
