'''
This file implements custom datatypes for the Lua data tables. Notably, this
helps fix issues like the potential for multiple forms of specifications.
'''

mining_schema = [{
        "amount_max": { "optional": False, "type": "float" },
        "amount_min": { "optional": False, "type": "float" },
        "name": { "optional": False, "type": "string" },
        "type": { "optional": False, "type": "string" },
        "probability": { "optional": False, "type": "float" }
}]

def mining_results(data, lua, output_dict):
    from factorio_schema import parse_data_value
    # First level of lua is a dict, watch out!
    if 'results' in lua:
        arr = parse_data_value(mining_schema, data, lua['results']) 
        claimed = ['results']
    else:
        arr = [{
            'count': lua.get('count', 1),
            'name': lua['result'],
            'type': 'item',
            'probability': 1.0
        }]
        claimed = ['result', 'count']
    output_dict['results'] = arr
    return claimed

def _map_array(lua_array, out_dict):
    for element in lua_array.values():
        if element.type:
            name = element.name
            ty = element.type
            amount = element.amount
        else:
            name = element[1]
            ty = "item"
            amount = element[2]
        out_dict[name] = amount
    return

def recipe_ingredients(data, lua):
    ingredients = {}
    _map_array(lua.ingredients, ingredients)
    return (ingredients, ['ingredients'])

def recipe_results(data, lua):
    results = {}
    if lua.result:
        results[lua.result] = lua.result_count if lua.result_count else 1
        return (results, ['result', 'result_count'])
    else:
        _map_array(lua.results, results)
        return (results, ['results'])
