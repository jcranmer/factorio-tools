function load_page() {
  load_crafting_info()
    .then(_ => load_tables(['l10n', 'resource-category']))
    .then(init_page);
}

var resource_listing = {}, miners = {};

function build_mapping(categories, items, makers, maker_name) {
  var listing = {}, maker_map = {};
  for (let key in categories) {
    listing[key] = [];
    maker_map[key] = [];
  }

  for (let item in items) {
    listing[items[item].category].push(items[item]);
  }
  for (let maker in makers) {
    for (let category of makers[maker][maker_name])
      maker_map[category].push(makers[maker]);
  }

  for (let key in categories) {
    if (listing[key].length == 0) {
      delete listing[key];
      delete maker_map[key];
    }
  }

  return [listing, maker_map];
}

function init_page() {
  fix_recipes();

  // Compile a list of the resource_categories -> resources
  [resource_listing, miners] = build_mapping(tables['resource-category'],
      tables.resource, tables['mining-drill'], 'resource_categories');

  // Select assembler lists
  build_assembler_selection();

  // Build the actual table.
  build_recipe_table();
}

function build_category_selector(category) {
  document.body.appendChild(document.createTextNode(category));
  for (let item of resource_listing[category]) {
    var img = document.createElement("img");
    img.src = 'image/' + item.icon;
    document.body.appendChild(img);
  }
}

function mine_per_second(ore, miner) {
  let base = (miner.mining_power - ore.minable.hardness) * miner.mining_speed /
    ore.minable.mining_time;
  // For infinite ores, multiply by yield (current / normal). The minimum field
  // gives the minimum yield.
  if (ore.infinite)
    base *= ore.minimum / ore.normal;
  let results = {};
  for (let result of ore.minable.results) {
    let count = 0;
    if (result.amount_min !== undefined)
      count = d3.mean([result.amount_min, result.amount_max]);
    else
      count = result.count;
    results[result.name] = base * count * result.probability;
  }
  return results;
}

var assemblers = new Map();

function build_assembler_selection() {
  var builder_tables = ['assembling-machine', 'furnace'].map(t => tables[t]);

  // Get the list of categories.
  var categories = new Map();
  for (var table of builder_tables) {
    for (var key in table) {
      for (var category of table[key].crafting_categories)
        if (!categories.has(category))
          categories.set(category, []);
    }
  }

  // Now, map the categories to the machines that can build them.
  for (var table of builder_tables) {
    for (var key in table) {
      for (var category of table[key].crafting_categories)
        categories.get(category).push(table[key]);
    }
  }
  for (var [name, arr] of categories.entries()) {
    arr.sort((a, b) => b.crafting_speed - a.crafting_speed);
    assemblers.set(name, arr[0]);
  }

  var selection_details = d3.select("div#building-selection")
    .selectAll("div")
    .data(Array.from(categories.entries()))
    .enter().append("div");

  selection_details
    .text(d => d[0] + ":  ");

  var options = selection_details.append("select")
    .selectAll("option").data(d => d[1]).enter().append("option");

  options.text(d => d.name + " (×" + d.crafting_speed + ")")
    .attr("value", d => d.name);

  selection_details.on("change", function (d) {
    var value = d3.event.target.value;
    assemblers.set(d[0], d[1].find(v => v.name == value));
    build_recipe_table();
  });

}

// Compute the rate of production for a recipe. 
function production_rate(recipe) {
  var assembler = assemblers.get(recipe.category);
  return assembler.crafting_speed / recipe.energy_required;
}

function get_ratio(recipe) {
  var rate = production_rate(recipe);
  var ratios = {};
  for (var ingredient in recipe.ingredients) {
    var in_recipe = tables.recipe[ingredient];
    var ingredient_rate = production_rate(in_recipe)
      * in_recipe.results[ingredient]
      / recipe.ingredients[ingredient];
    ratios[ingredient] = ingredient_rate / rate;
  }
  return ratios;
}

function continued_fraction(x) {
  var orig = x;
  var remainders = [];
  function approx() { return remainders.reduceRight((b, a) => a + 1 / b); }
  do {
    var r = Math.floor(x);
    remainders.push(r);
    x = 1 / (x - r);
  } while (Math.abs(approx() - orig) / orig > 1e-6);
  return remainders;
}

function simplify(ratio, max_denom) {
  var remainders = continued_fraction(ratio);
  var h = [0, 1], k = [1, 0];
  for (var i = 0; i < remainders.length; i++) {
    var hn = remainders[i] * h[i + 1] + h[i];
    var kn = remainders[i] * k[i + 1] + k[i];
    if (kn > max_denom)
      break;
    h.push(hn);
    k.push(kn);
  }

  var hn = h[h.length - 1], kn = k[k.length - 1];
  if (hn / kn < ratio - 1e-6)
    hn++;

  return [hn, kn];
}

function build_recipe_table() {
  let recipes = Object.keys(tables.recipe).map(t => tables.recipe[t]);
  let ratios = {};
  for (let r of recipes) {
    let ing = new Map();
    try {
      let ratio = get_ratio(r);
      for (let k in ratio) {
        ing.set(k, simplify(ratio[k], 100));
      }
    } catch (e) {
      // Ignore it, some of the recipes don't have ratios.
    }
    ratios[r.name] = ing;
  }
  let table = d3.select("#ratio-list").selectAll("tr").data(recipes);

  table.exit().remove();
  table = table.enter().append("tr").merge(table);

  let headNodes = table.selectAll("td").data(t => [t]);
  headNodes.exit().remove();
  headNodes = headNodes.enter()
    .append("td");
  headNodes.html(t => "<img src=\"image/" + t.icon + "\"> " + t.name);

  table.append("td").html(function (r) {
    let reqs = Array.from(ratios[r.name].entries());
    reqs = reqs.map(function ([req, ratio]) {
      let img = req in tables['full-item'] ? 
        "<img src=\"image/" + tables['full-item'][req].icon + "\">" :
        "";
      return ratio[0] + " : " + ratio[1] + " " + img + req;
    });
    return reqs.join('<br>');
  });
}
