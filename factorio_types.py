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

#              "results": { "optional": true, "type": [{
#                "amount_max": { "optional": false, "type": "float" },
#                "amount_min": { "optional": false, "type": "float" },
#                "name": { "optional": false, "type": "string" },
#                "type": { "optional": false, "type": "string" },
#                "probability": { "optional": false, "type": "float" }
#              }], "default": [] }
