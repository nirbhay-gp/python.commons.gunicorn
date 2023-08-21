import falcon
import datetime as dt
import json

class Ping():
    def on_get(self, req: 'falcon.Request', resp: 'falcon.Response', *args, **kwargs):
        resp.text = json.dumps({ 'version': '1.0.0', 'timestamp': dt.datetime.utcnow().isoformat() })

app = falcon.App()

app.add_route('/ping', Ping())