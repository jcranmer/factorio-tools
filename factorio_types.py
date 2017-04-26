'''
This file implements custom datatypes for the Lua data tables. Notably, this
helps fix issues like the potential for multiple forms of specifications.
'''

mining_schema = [{
        "amount": { "optional": True, "type": "float", "default": 0 },
        "amount_max": { "optional": True, "type": "float", "default": 0 },
        "amount_min": { "optional": True, "type": "float", "default": 0 },
        "name": { "optional": False, "type": "string" },
        "type": { "optional": False, "type": "string" },
        "probability": { "optional": True, "type": "float", "default": 1.0 }
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

def encode_lua(obj):
    resp = dict()
    for key, value in obj.items():
        resp[key] = value
    if all(x + 1 in resp for x in range(len(resp))):
        return list(resp[x + 1] for x in range(len(resp)))
    return resp
def _map_array(lua_array, out_dict):
    for element in lua_array.values():
        if element.name:
            name = element.name
            ty = element.type or 'item'
            if element.amount is not None:
                amount = element.amount
                if element.probability:
                    amount *= element.probability
            else:
                amount = (element.amount_max + element.amount_min) / 2.0
        else:
            name = element[1]
            ty = "item"
            amount = element[2]
        out_dict[name] = amount
    return

def recipe_ingredients(data, lua):
    if not lua.ingredients:
        return recipe_ingredients(data, lua.normal)
    ingredients = {}
    _map_array(lua.ingredients, ingredients)
    return (ingredients, ['ingredients'])

def recipe_results(data, lua):
    results = {}
    if lua.result:
        results[lua.result] = lua.result_count if lua.result_count else 1
        return (results, ['result', 'result_count'])
    elif lua.results:
        _map_array(lua.results, results)
        return (results, ['results'])
    else:
        return recipe_results(data, lua.normal)

picture_schema = {
    "animation_speed": {"optional": True, "type": "float", "default": 1.0},
    "apply_projection": {"optional": True, "type": "bool", "default": False},
    "direction_count": {"optional": True, "type": "integer", "default": 4},
    "filename": {"optional": False, "type": "FileName"},
    "flags": {"optional": True, "type": ["string"], "default": []},
    "frame_count": {"optional": True, "type": "integer", "default": 1},
    "height": {"optional": False, "type": "integer"},
    "line_length": {"optional": True, "type": "integer", "default": 1},
    "priority": {"optional": True, "type": "string", "default": "normal"},
    "scale": {"optional": True, "type": "float", "default": 1.0},
    "shift": {"optional": True, "type": ["float"], "default": [0, 0]},
    "tint": {"optional": True, "default": None, "type": {
        "r": {"optional": False, "type": "float"},
        "g": {"optional": False, "type": "float"},
        "b": {"optional": False, "type": "float"},
        "a": {"optional": True, "type": "float", "default": 1.0}
    }},
    "variation_count": {"optional": True, "type": "integer", "default": 1},
    "width": {"optional": False, "type": "integer"},
    "x": {"optional": True, "type": "integer", "default": 0},
    "y": {"optional": True, "type": "integer", "default": 0}
}

animation_schema = dict(picture_schema)
animation_schema.update({
    "axially_symmetrical": {"optional": True, "type": "bool", "default": True},
    "blend_mode": {"optional": True, "type": "string", "default": ""},
    "duration": {"optional": True, "type": "integer", "default": 0},
    "fade_away_duration": {"optional": True, "type": "integer", "default": 0}
})

def entity_animation(data, lua):
    return (None, []) # XXX skip brokenness for now
    from factorio_schema import parse_data_value
    def parse_block(lua_block, schema):
        keys = list(lua_block.keys())
        if keys == range(1, len(keys) + 1):
            d = [parse_block(lua_block[k], schema) for k in keys]
        elif 'filename' in keys:
            d = parse_data_value(schema, data, lua_block)
        elif 'layers' in keys or 'sheet' in keys:
            # XXX: fix me.
            d = {}
        else:
            d = []
            for k in keys:
                val = parse_block(lua_block[k], schema)
                # Rail remnants are PITAs. May need to change tack here.
                if isinstance(val, dict):
                    val['name'] = k
                d.append(val)
        return d

    if 'animation' in lua:
        d = parse_block(lua.animation, animation_schema)
        return (d, ['animation'])
    elif 'pictures' in lua:
        d = parse_block(lua.pictures, picture_schema)
        return (d, ['pictures'])
    elif 'picture' in lua:
        d = parse_block(lua.picture, picture_schema)
        return (d, ['picture'])
    else:
        return (None, [])

def tech_effects(data, lua):
    from factorio_schema import encode_lua
    d = {'recipes': [], 'modifiers': []}
    if 'effects' not in lua:
        return (d, [])
    for effect in lua.effects.values():
        if effect.type == 'unlock-recipe':
            d['recipes'].append(effect.recipe)
        elif 'modifier' in effect:
            d['modifiers'].append(encode_lua(effect))
        else:
            raise Exception("Unknown technology effect: %s" % str(list(effect.keys())))
    return (d, ['effects'])


complex_types = [
]
