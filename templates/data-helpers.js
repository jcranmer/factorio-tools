var tables = new Map();

/**
 * Promise to load a table.
 */
function load_table(name) {
  return new Promise((resolve, reject) => {
    if (tables.has(name))
      return resolve(tables.get(name));
    d3.json('data/' + name + '.json', function (error, data) {
      if (error)
        reject(error);
      tables.set(name, data);
      tables[name] = data;
      resolve(data);
    });
  });
}

/**
 * Helper for loading multiple tables at once.
 */
function load_tables(table_names) {
  return Promise.all(table_names.map(t => load_table(t)));
}

/**
 * Promise to load all tables that we need for crafting information.
 */
function load_crafting_info() {
  return load_tables(['assembling-machine', 'furnace', 'full-item',
    'item-group', 'item-subgroup', 'mining-drill', 'recipe', 'resource']);
}
