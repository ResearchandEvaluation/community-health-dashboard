"""Regenerate site/template.html from the Claude prototype file (Main.dc.html) by replacing its embedded data
with placeholders and its /_blob/ image links with assets/. Usage: python3 build/make_template.py <Main.dc.html>"""
import sys, os, re
src = sys.argv[1]; s = open(src).read()
helm = s[s.index("<helmet>") + 8:s.index("</helmet>")]
style = helm[helm.index("<style>") + 7:helm.index("</style>")]
body = s[s.index("</helmet>") + 9:s.index("</x-dc>")]
logic = s[s.index("class Component"):s.index("</script>", s.index("class Component"))]
amap = {"057f5e1aeaa5710adbca694210de2407":"phil-logo.png","9ccd505b122a3d68afa0a523b7412be7":"phil-mark.png","d9b486202459f8d1f091786e465b2310":"fox-magnifier.png","63047fc99f557382da29ad8d6a26f9ea":"fox-clipboard.png","0d8f573c3397239359438ec85b3b838f":"fox-hammer.png","4e696074658836cc8b977776c61c298f":"fox-wrench.png","f3f440bf625c229b8de1a33de8014ec0":"fox-pointing.png","62aacf48f676749d3bfe4de3b20ae44b":"fox-welcome.png","951f9eb19bae326623019238cd091bdf":"fox-lightbulb.png"}
for k, v in amap.items():
    body = body.replace(f"/_blob/{k}", f"assets/{v}"); logic = logic.replace(f"/_blob/{k}", f"assets/{v}")
assert "/_blob/" not in body + logic
def ph(name, var):
    global logic
    a = logic.index(f"    var {var} = "); b = logic.index(";\n", a)
    logic = logic[:a] + f"    var {var} = __{name}__" + logic[b:]
for v in ["INDD", "ECM_USE", "MCP_PLANS", "ECMD_PUB", "ECMD", "RES", "ACT", "STRATA"]: ph(v, v)
tpl = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Community Health Data Dashboard | Population Health Innovation Lab</title>
<meta name="description" content="Public data on health needs and services in the 17 California counties where PHIL works, alongside PHIL's work with community partners.">
<link rel="icon" href="assets/phil-mark.png">
<style>{style}</style>
<style>.phil-loading{{font-family:Arial,sans-serif;padding:40px;color:#12365b}}</style>
</head>
<body>
<div id="phil-root"><div class="phil-loading">Loading the Community Health Data Dashboard…</div></div>
<script type="text/template" id="phil-template">{body}</script>
<script type="text/plain" id="phil-logic">{logic}</script>
<script src="runtime.js"></script>
<!-- Built __BUILD_DATE__ -->
</body>
</html>'''
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "template.html")
open(out, "w").write(tpl); print("template written", len(tpl))
