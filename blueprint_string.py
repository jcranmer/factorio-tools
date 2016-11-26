import base64
import collections
import factorio
import gzip
import lupa
from PIL import Image
import re
import StringIO

def make_table(lua_table):
    if isinstance(lua_table, unicode) or isinstance(lua_table, int) \
            or isinstance(lua_table, float):
        return lua_table
    keys = list(lua_table.keys())
    if keys == range(1, len(keys) + 1):
        return [make_table(lua_table[i + 1]) for i in range(len(keys))]
    val = dict((key, make_table(lua_table[key])) for key in keys)
    table_clazz = collections.namedtuple('Struct', keys)
    return table_clazz(**val)

def json_results(blueprint):
    fd = StringIO.StringIO(base64.b64decode(blueprint))
    with gzip.GzipFile(fileobj=fd) as gzfd:
        string = gzfd.read()

    subs = {
        'basic-accumulator': 'accumulator',
        'basic-armor': 'light-armor',
        'basic-beacon': 'beacon',
        'basic-bullet-magazine': 'firearm-magazine',
        'basic-exoskeleton-equipment': 'exoskeleton-equipment',
        'basic-grenade': 'grenade',
        'basic-inserter': 'inserter',
        'basic-laser-defense-equipment': "personal-laser-defense-equipment",
        'basic-mining-drill': "electric-mining-drill",
        'basic-modular-armor': "modular-armor",
        'basic-splitter': "splitter",
        'basic-transport-belt': "transport-belt",
        'basic-transport-belt-to-ground': "underground-belt",
        'express-transport-belt-to-ground': "express-underground-belt",
        'fast-transport-belt-to-ground': "fast-underground-belt",
        'piercing-bullet-magazine': "piercing-rounds-magazine",
        'smart-chest': "steel-chest",
        'smart-inserter': "filter-inserter"
    }
    string = re.sub('(\\w|-)+', lambda m: subs[m.group(0)] if m.group(0) in subs else m.group(0), string)
    lua_table = lupa.LuaRuntime().execute(string)
    return make_table(lua_table)

def get_blueprint_image(data, entity, entity_data):
    print entity
    entity_data = entity_data[entity.name]
    if entity_data.animation is None:
        return (Image.new("RGBA", (0, 0)), (0, 0))# Skip me for now.

    # Grab the base image that we want to display. The first frame of the
    # animation should do fine.
    ani = entity_data.animation
    if isinstance(ani, list):
        return (Image.new("RGBA", (0, 0)), (0, 0))# Skip me for now.

    base_image = Image.open(
        StringIO.StringIO(data.load_path(ani['filename'])))

    # For directions, select the row based on direction.
    y = 0
    if hasattr(entity, 'direction'):
        y = entity.direction * ani['height']
    # The region we want to extract is [x, y] -> [x + width, y + height]
    region = base_image.crop((ani['x'], y, ani['x'] + ani['width'], y + ani['height']))

    # Okay, where do we stick this? The entity is centered on the position in
    # the blueprint (measured in tiles, so multiply by 32 to get actual value).
    # We need the upper-left. So stick the center on the position indicated.
    image_center = [32 * (entity.position.x + ani['shift'][0]), 32 * (entity.position.y + ani['shift'][1])]
    top_left = [image_center[0] - region.width / 2, image_center[1] - region.height / 2]
    return (region, (int(top_left[0]), int(top_left[1])))

def make_image(blueprint_table):
    data = factorio.load_factorio()
    entity_data = data.load_pseudo_table('entity')
    # Convert all entities into images
    images = [get_blueprint_image(data, entity, entity_data)
        for entity in blueprint_table.entities]

    # Compute the bounds for the image. Note that some offsets are negative.
    bounds = (0, 0, 0, 0)
    for im, off in images:
        bounds = (
            min(off[0], bounds[0]),
            min(off[1], bounds[1]),
            max(off[0] + im.width, bounds[2]),
            max(off[1] + im.height, bounds[3]))

    # With those bounds, create the new image, and paste the images as
    # necessary.
    image = Image.new("RGBA", (bounds[2] - bounds[0], bounds[3] - bounds[1]))
    for im, off in images:
        image.paste(im, (off[0] - bounds[0], off[1] - bounds[1]), im)
    image.show()

if __name__ == '__main__':
    import sys
    make_image(json_results(sys.argv[1]))
