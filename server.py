import factorio
import flask
import json

app = flask.Flask(__name__)
data = factorio.load_factorio()

@app.route('/image/<path:image>')
def show_image(image):
    resp = flask.Response(mimetype="image/jpeg")
    resp.set_data(data.load_path(image))
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
    resp = flask.Response(mimetype="application/json")
    json.dump(dict((n, v.to_json()) for n, v in data.load_table(table).items()),
        resp.stream, sort_keys=True)
    return resp

if __name__ == '__main__':
    app.run(debug=True)
