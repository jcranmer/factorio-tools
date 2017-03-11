import factorio
import flask
import json
from PIL import Image, ImageChops
import StringIO
import sys

app = flask.Flask(__name__)
if len(sys.argv) > 1:
    data = factorio.load_factorio(mod_path=sys.argv[1])
else:
    data = factorio.load_factorio()

@app.route('/image/<path:image>')
def show_image(image):
    resp = flask.Response(mimetype="image/png")
    resp.set_data(data.load_path(image))
    return resp

@app.route('/icon/<table>/<entry>')
def show_icon(table, entry):
    try:
        entry = data.load_pseudo_table(table)[entry]
    except KeyError:
        flask.abort(404)
    if entry.icon:
        return show_image(entry.icon)
    elif entry.icons == [] and table == "recipe":
        keys = entry.results.keys()
        assert len(keys) == 1
        return show_icon("item", keys[0])

    # Get the icons, and add the layers to the icons.
    icons = entry.icons
    base_icon = icons[0]
    image = Image.open(StringIO.StringIO(
        data.load_path(base_icon['icon'])))
    image = Image.new("RGBA", image.size)

    for icon in icons:
        if icon['icon']:
            sub_image = Image.open(StringIO.StringIO(data.load_path(icon['icon'])))
        else:
            sub_image = Image.new("RGBA", image.size, (1, 1, 1, 1))
        if icon['tint']:
            def tint_component(base, tint):
                x = float(base)/256.0
                weight = x - 0.5
                val = x + tint * (1.0 - 4.0 * weight * weight)
                return int(val*256)
            tints = [icon['tint'].get(c, 0.0) for c in "rgba"]
            tints[0] *= tints[-1]
            tints[1] *= tints[-1]
            tints[2] *= tints[-1]
            def tint_value(val):
                return (tint_component(val[0], tints[0]),
                        tint_component(val[1], tints[1]),
                        tint_component(val[2], tints[2]),
                        tint_component(val[3], tints[3]))
            pix = sub_image.load()
            for row in range(sub_image.size[0]):
                for col in range(sub_image.size[1]):
                    val = tint_value(pix[row, col])
                    pix[row, col] = val
        image.paste(sub_image, None, sub_image)

    # Convert the image into a response.
    resp = flask.Response(mimetype="image/png")
    respfd = StringIO.StringIO()
    image.save(respfd, "png")
    resp.set_data(respfd.getvalue())
    respfd.close()
    return resp

@app.route('/data/lua_raw.json')
def full_lua():
    def encode_lua(obj):
        resp = dict()
        for key, value in obj.items():
            resp[key] = value
        if all(x + 1 in resp for x in range(len(resp))):
            return list(resp[x + 1] for x in range(len(resp)))
        return resp
    resp = flask.Response(mimetype="application/json")
    json.dump(data.lua.globals().data.raw, resp.stream, default=encode_lua,
            sort_keys=True)
    return resp

@app.route('/data/<table>.json')
def json_table(table):
    if table not in data._data:
        flask.abort(404)
    resp = flask.Response(mimetype="application/json")
    json.dump(dict((n, v.to_json()) for n, v in data.load_table(table).items()),
        resp.stream, sort_keys=True)
    return resp

@app.route('/data/full-<table>.json')
def json_full_table(table):
    resp = flask.Response(mimetype="application/json")
    json.dump(dict((n, v.to_json()) for n, v in data.load_pseudo_table(table).items()),
        resp.stream, sort_keys=True)
    return resp

@app.route('/data/l10n.json')
def json_data():
    resp = flask.Response(mimetype="application/json")
    json.dump(data.get_l10n_tables(), resp.stream, sort_keys=True)
    return resp

@app.route('/item-info')
def item_info():
    return flask.render_template('item-info.html')

@app.route('/tech-tree')
def tech_tree():
    return flask.render_template('tech-tree.html')

@app.route('/ratio')
def ratio():
    return flask.render_template('ratio.html')

@app.route('/')
def index():
    return flask.render_template('index.html')

# XXX
@app.route('/scripts/<path:script>')
def script(script):
    return flask.render_template(script)

if __name__ == '__main__':
    app.run(debug=True)
