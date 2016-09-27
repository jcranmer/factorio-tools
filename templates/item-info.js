function load_page() {
  load_crafting_info()
    .then(_ => load_tables(['l10n', 'technology']))
    .then(init_page);
}

function init_page() {
  fix_recipes();

  make_item_selector(document.getElementById("group"),
    tables['item-group'], tables['item-subgroup'], [tables['full-item'], tables['fluid']],
    change_item);
}

function change_item(item) {
  if (typeof item == "string") {
    item = item in tables.fluid ? tables.fluid[item] : tables['full-item'][item];
  }
  d3.select("h2#title").text(item.name);
  var sources = get_values('recipe').filter(r => item.name in r.results);
  var sinks = get_values('recipe').filter(r => item.name in r.ingredients);
  display_recipes(sources, document.getElementById("sources"));
  display_recipes(sinks, document.getElementById("uses"));
}

function display_recipes(recipes, el) {
  var techs = get_values('technology');
  var rows = d3.select(el).selectAll("tr").data(recipes);
  rows.exit().remove();
  rows = rows.enter().append("tr").merge(rows);

  // Forcibly clear prior contents
  rows.html("");

  var headNodes = rows.selectAll("td").data(t => [t]);
  headNodes.exit().remove();
  headNodes = headNodes.enter()
    .append("td");
  headNodes.html(name_item);

  rows.append("td").html(function (recipe) {
    var ingredients = Object.keys(recipe.ingredients);
    return ingredients.map(ing =>
        recipe.ingredients[ing] + "× " +
        "<a onclick=\"change_item('" + ing + "')\">" + name_item(ing) + "</a>");
  });
  rows.append("td").html(function (recipe) {
    var results = Object.keys(recipe.results);
    return results.map(ing =>
        recipe.results[ing] + "× " +
        "<a onclick=\"change_item('" + ing + "')\">" + name_item(ing) + "</a>");
  });
  rows.append("td").html(function (recipe) {
    return recipe.category;
  });
  rows.append("td").html(function (recipe) {
    return techs.filter(t => t.effects.recipes.includes(recipe.name))
      .map(t => t.name)
      .join(", ");
  });
}
