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
        "mainEntityOfPage": url, "recipeCategory": categories,
        "recipeIngredient": ingredients,
        "recipeInstructions": [{"@type": "HowToStep", "position": i+1, "text": x} for i, x in enumerate(method)]
    }
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
        parts.append(f'<img class="recipe-image" src="{esc(image)}" alt="{esc(name)}">')
    parts.append('<h2>Ingredients</h2><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in ingredients) + '</ul>')
    parts.append('<h2>Method</h2><ol>' + ''.join(f'<li>{esc(x)}</li>' for x in method) + '</ol>')
    parts.append(f'<a class="back" href="/?recipe={esc(recipe.get("id",""))}">View this recipe in the recipe book</a></article></main></body></html>')
    return ''.join(parts)

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
