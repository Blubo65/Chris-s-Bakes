# Chris's Bakes

A simple GitHub Pages recipe book for Chris's air-fryer recipes.

## Adding a recipe

The safest way to add a recipe is through the website's **Add recipe** button while signed in.

Each recipe is stored with a stable ID, complete ingredients/method, creation date and optional photo. Recipe photos uploaded through the website are stored in Supabase Storage rather than inside the HTML file.

## If adding a starter recipe in the code

1. Give it a **unique ID**. Do not reuse an existing recipe ID.
2. Include at least `id`, `name`, `category`, `ingredients` and `method`.
3. If it has a repository photo, make sure the exact filename (including spaces and capitalisation) exists in the repository.
4. Do not add a recipe to a separate sync list. Complete starter recipes are now merged automatically.
5. Do not add hard-coded photo mappings unless the recipe genuinely needs a legacy filename fallback.
6. Do not delete a recipe from `STARTER_RECIPES` just to hide it. Use the existing deletion mechanism so it is not reintroduced during sync.

## Backups

The website's **Backup** button creates a versioned JSON backup of the recipes and deletion list. Keep a downloaded backup before making major changes.

The repository also has dated Git branches used as safety points before maintenance changes.

## Automatic checks

Every push to `main` runs the website validation workflow. It checks:

- valid starter-recipe data
- duplicate recipe IDs
- required recipe fields
- missing local image files
- JavaScript syntax

Legacy image/cover workflows are manual-only so adding or editing a recipe cannot unexpectedly overwrite the site.

## Important

The website uses a Supabase publishable key in the browser. This is expected for a client-side Supabase app; the database and Storage **RLS policies must remain correctly restricted** so only the owner can edit recipe data or upload files.
