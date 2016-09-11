function make_item_selector(container, groups, subgroups, item_tables) {
  function sort_order(a, b) {
    if (a.order < b.order)
      return -1;
    else if (a.order > b.order)
      return 1;
    return 0;
  }

  var group_vals = Object.keys(groups).map(t => groups[t]);
  group_vals.sort(sort_order);

  // Assign a sort index for every subgroup within a group.
  var subgroup_vals = Object.keys(subgroups).map(t => subgroups[t]);
  subgroup_vals.sort(sort_order);
  var nested = d3.nest().key(d => d.group)
    .entries(subgroup_vals)
    .forEach(group => group.values.forEach((d, i) => d.sortIndex = i));

  // Build the list of items for the table.
  var items = [];
  for (var table of item_tables) {
    items = items.concat(Object.keys(table).map(i => table[i]));
  }
  items.sort(sort_order);

  // Clear out the groups for which no items exist.
  group_vals = group_vals.filter(
      g => items.some(i => subgroups[i.subgroup].group == g.name));

  var image_list = document.createElement("div");
  image_list.className = "item-selector";
  document.getElementById("group").appendChild(image_list);

  var group_imgs = d3.select("div#group")
    .selectAll("img")
    .data(group_vals);

  group_imgs
    .enter().append("img")
    .attr("src", g => "image/" + g.icon)
    .attr("title", g => tables.l10n['item-group-name'][g.name])
    .attr("width", 64).attr("height", 64)
    .on("click", function (d) {
      var nodes = d3.select(image_list).selectAll("div")
        .data(subgroup_vals.filter(sg => sg.group == d.name));
      nodes.exit().remove();
      nodes = nodes.enter().append("div")
        .classed("subgroup", true)
        .merge(nodes);

      var item_imgs = nodes.selectAll("img")
        .data(sg => items.filter(function (item) {
          return item.subgroup == sg.name && sg.group == d.name;
        }));
      item_imgs.exit().remove();
      item_imgs.enter().append("img")
        .merge(item_imgs)
        .attr("src", item => "image/" + item.icon)
        .attr("title", item => tables.l10n["item-name"][item.name])
        .attr("width", 32).attr("height", 32);
    });

  d3.select(image_list).raise();
}

/**
 * Add icon, subgroup, and order to the recipes table from the full-item table.
 */
function fix_recipes() {
  var recipes = tables.get('recipe'), items = tables.get('full-item');
  for (var key in recipes) {
    if (key in items) {
      var item = items[key], recipe = recipes[key];
      recipe.icon = item.icon;
      recipe.subgroup = item.subgroup;
      recipe.order = item.order;
    }
  }
}

function get_craftables() {
}
