"""Copy gift.json into indices.json without touching the other four indices.
Run by the 'Update GIFT Nifty' workflow after gift.json changes."""
import json, os
d = os.path.dirname(os.path.abspath(__file__))
idx = json.load(open(os.path.join(d, "indices.json")))
g = json.load(open(os.path.join(d, "gift.json")))
row = {"name": "GIFT NIFTY", **{k: v for k, v in g.items() if k != "name"}}
idx["indices"] = [x for x in idx["indices"] if x["name"] != "GIFT NIFTY"] + [row]
json.dump(idx, open(os.path.join(d, "indices.json"), "w"), indent=1)
print(json.dumps(row))
