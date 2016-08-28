'''
This contains Python data types for the Lua data prototypes. Almost all of the
classes here are loaded dynamically from a schema.json file.

If you run the file directly, you can verify the correctness of the schema.
'''

import functools
import json

def make_wrapper_object(data, lua_object):
    '''Wrap the lua_object into a class using the data as the container for all
    the relevant factorio data.'''
    return classes[get_class_name(lua_object.type)](data, lua_object)

def get_all_tables(pseudo_name):
    '''This returns the list of all tables that comprise the subclasses of the
    given type.'''
    return classes[get_class_name(pseudo_name)].tables

class FactorioData(object):
    '''The base class for all data coming from the lua.data table.'''
    def __init__(self, data, lua_object):
        self.data = data
        self.lua = lua_object

    @property
    def name(self):
        '''The key in the table of this data object. Other properties may refer
        to this thing by this name. The localization also uses this name to find
        the localization key.

        Type: string
        Mandatory'''
        return self.lua.name

    @property
    def type(self):
        '''The table in which this thing will be inserted.

        Type: string
        Mandatory'''
        return self.lua.type

    prop_list = ['name', 'type']

    def to_json(self):
        '''Returns a JSON-ifiable dictionary for this data member.'''
        return dict((prop, getattr(self, prop)) for prop in self.prop_list)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.lua.name)

# Load our schema file.
with open('schema.json') as schemafd:
    schema = json.load(schemafd)

def get_class_name(entity_type):
    '''Convert a table (pseudo-)name into a class name in this module.'''
    return str(''.join(x.capitalize() for x in entity_type.split('-')))

#######
# The following methods are used to find out how to parse data from the
# schema.json file. In lieu of having a better place, let's describe the basics
# of the schema file here.
#
# As you'll recall, the Lua raw data is effectively a table of tables, each
# table corresponding to a non-abstract class (this makes abstract classes hard
# to find). The schema file is a single dictionary that uses the class names, in
# table form, that maps to information about their class data.
#
# The class data consists of a few keys:
# - parent (mandatory): the name of the parent class
# - abstract (optional, default: false): If true, we don't expect a table for
#   this class.
# - properties (optional, default: {}): This is a dictionary of the descriptors
#   for property values, as explained below. The keys are the names of the
#   properties, and the values are the descriptors themselves.
#
# Property descriptors can be recursive for complex datatypes. Some of the
# information here is subject to change. The optional and type properties must
# always be present. If optional is set to false, then a default value must be
# specified. Note that the default value should be specified in the JSON-ified
# version of the Lua data.
#
# The type of a property descriptor illustrates how to parse it. Simple
# properties are described with a string. Most of the strings are found in the
# data_types table below (the next few functions are helpers for the conversion
# functions). In addition to those strings, it is possible to use a Python
# class name to refer to an instance of that type (this includes abstract
# classes like Entity).
#
# More complex types have different forms (note that the recursion):
# - A list containing a single descriptor type. This means that the value must
#   be a list of values conforming to that type.
# - A list starting with the string "tuple" and containing several succeeding
#   descriptor types. This means that the value must have exactly that many
#   elements and conforming to the respective types.
# - A dictionary whose keys are property names and whose values are property
#   descriptors (which is to say, they are dicts with optional/type/default
#   parameters, not the simple string/list/etc. descriptor types). Unlike the
#   top-level descriptors, absent keywords are not permissible.
# - An empty string. This means that the type is not described, and is therefore
#   reflected in raw form.
def find_in_tables(names, data, val):
    # Not all tables might be present (there may be a few cases where the schema
    # says something isn't abstract, but it turns out to be abstract).
    if val is not None and not any(
            data._data[name] and val in data._data[name] for name in names):
        raise Exception("Unknown %s: %s" % (name, val))
    return val

def coerce_type(val, ty):
    if isinstance(val, unicode):
        val = str(val)
    if isinstance(val, int) and ty == float:
        val = float(val)
    if val is not None and not isinstance(val, ty):
        raise Exception("Bad type, got %s expected %s" % (type(val).__name__, ty.__name__))
    if val is None and ty in (float, int):
        raise Exception("Got null when expected %s" % ty.__name__)
    return val

# Bool is special--it may be true, false, "true", or "false"
def coerce_bool(data, val):
    if isinstance(val, bool):
        return val
    if val == "true":
        return True
    elif val == "false":
        return False
    raise Exception("Unknown bool value: %s" % repr(val))

# This is the list of data type matchings for Lua data. It is defined as a table
# of schema type name -> conversion function
data_types = {
    'FileName': lambda data, val: coerce_type(val, str),
    'bool': coerce_bool,
    'float': lambda data, val: coerce_type(val, float),
    'integer': lambda data, val: coerce_type(val, int),
    'string': lambda data, val: coerce_type(val, str),
    # Catch-all for data whose schema is not yet known
    '': lambda data, val: val
}

def parse_data_value(schema_type, data, value):
    '''Parse and convert the value according to the descriptor type. The data
    parameter is the reference to the Factorio context variable.'''

    # Simple data
    if isinstance(schema_type, unicode):
        return data_types[schema_type](data, value)

    # Convert tables into lists or dictionaries as appropriate
    if type(value).__name__ == '_LuaTable':
        value = encode_lua(value)

    if isinstance(schema_type, list):
        # Check that the value is also a list
        if not isinstance(value, list):
            raise Exception("Expected a list, got %s" % repr(value))
        # This is a [type, type, type, ...] kind of list
        if len(schema_type) == 1:
            return [parse_data_value(schema_type[0], data, x) for x in value]

        # This is a tuple kind of list
        if schema_type[0] == 'tuple':
            schemata = schema_type[1:]
            if len(schemata) != len(value):
                raise Exception("Expected %s, got %s" % (repr(schemata), repr(value)))
            return tuple(parse_data_value(t, data, x) for t, x in zip(schemata, value))

    if isinstance(schema_type, dict):
        # Check that value is also a dict
        if not isinstance(value, dict):
            raise Exception("Expected a dict, got %s" % repr(value))

        # Map each entry of the known dictionary. This is basically the same
        # schema as the type in the first place.
        converted_value = dict()
        for key, desc in schema_type.items():
            if key not in value:
                if not desc['optional']:
                    raise Exception("Missing key %s" % key)
                new_val = desc['default']
            else:
                new_val = value[key]
            converted_value[key] = parse_data_value(desc['type'], data, new_val)

        # Punish unknown_keys here.
        unknown_keys = set(value) - set(schema_type)
        if unknown_keys:
            raise Exception("Found unexpected keys: %s" % ', '.join(unknown_keys))
        return converted_value

    # Don't know this kind of schema
    raise Exception("Unknown schema: %s" % repr(schema_type))

def encode_lua(obj):
    '''Convert a LuaTable into a Python list or dict. This is not recursive.'''
    resp = dict()
    for key, value in obj.items():
        resp[key] = value
    if all(x + 1 in resp for x in range(len(resp))):
        return list(resp[x + 1] for x in range(len(resp)))
    return resp

class DataLoader(object):
    '''This is what we assign to be the property descriptor for each reflected
    property.'''
    def __init__(self, name, propdesc):
        self.__name__ = name
        self.schema = propdesc
        self.__doc__ = '''
            No documentation for this property.

            Type: %s
            %s''' % (str(propdesc['type']), 'Default: %s' % (repr(propdesc['default'])) if propdesc['optional'] else 'Mandatory')

    def __get__(self, inst, owner):
        if self.__name__ not in inst.lua:
            if not self.schema['optional']:
                raise Exception("Missing property %s on %s" %
                    (self.__name__, repr(self)))
            value = self.schema['default']
        else:
            value = inst.lua[self.__name__]
        return parse_data_value(self.schema['type'], inst.data, value)

    def __set__(self, inst, value):
        raise AttributeError("Cannot set %s" % self.__name__)

def make_class(name, parent):
    '''This creates a python class object with the given name and superclass.'''
    methods = dict()

    # Fill in properties from the schema definition
    for prop, descriptor in schema[name].get('properties', {}).items():
        methods[prop] = DataLoader(prop, descriptor)

    methods['prop_list'] = parent.prop_list + \
            list(schema[name].get('properties', {}))

    return type(get_class_name(name), (parent,), methods)

# Make the classes we need. The schema is in no particular order (python dicts
# don't guarantee insertion order), so we need to cycle through the list several
# times to guarantee parent classes get initialized before sub classes.
classes = dict()
unmade_classes = list(schema)
while unmade_classes:
    for name in unmade_classes:
        classname = get_class_name(name)
        parent_name = schema[name]['parent']
        if parent_name and get_class_name(parent_name) not in classes:
            continue
        unmade_classes.remove(name)

        # Get the superclass
        if parent_name:
            parent = classes[get_class_name(parent_name)]
        else:
            parent = FactorioData

        classes[classname] = make_class(name, parent)

# Export the classes. Dynamic scope magic for the win!
globals().update(classes)
__all__ = list(classes) + ['FactorioData', 'make_wrapper_object',
        'get_all_tables']

# Add onto each class the list of tables that it encompasses.
for name, clazz in classes.items():
    tlist = filter(lambda n:
        not schema[n].get('abstract', False) and
        issubclass(classes[get_class_name(n)], clazz), schema)
    clazz.tables = tlist
    data_types[name] = functools.partial(find_in_tables, tlist)

# If we run this file directly, validate the schema. This means dumping out the
# unknown tables, the unknown properties, and enforcing that all the elements
# verify properly.
if __name__ == '__main__':
    import factorio
    data = factorio.load_factorio()
    raw = data.lua.globals().data.raw
    tables = list(raw)
    tables.sort()
    for table in tables:
        if table not in schema:
            print 'Missing schema for %s' % table
            continue
        if schema[table].get('abstract', False):
            print 'Table %s should be abstract!' % table

        # Find missing keys
        unknown_keys = set()
        clazz = classes[get_class_name(table)]
        known_keys = clazz.prop_list
        for value in raw[table].values():
            unknown_keys.update(list(value))

            # Exercise the property getters
            wrapped = clazz(data, value)
            for key in known_keys:
                try:
                    getattr(wrapped, key)
                except:
                    print 'Property %s of %s has bad schema' % (key, table)
                    print 'Value for %s: ->%s<-' % (wrapped.name, wrapped.lua[key])
                    raise

        unknown_keys.difference_update(set(known_keys))
        if unknown_keys:
            print 'Missing properties for %s: %s' % (table, ', '.join(unknown_keys))
