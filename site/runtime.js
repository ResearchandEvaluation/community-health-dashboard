/* Minimal template runtime for the PHIL Community Health Data Dashboard.
   Renders the <x-dc> template with the values returned by Component.renderVals().
   Supports: {{dotted.path}} in text and attributes, <sc-for list as>, <sc-if value>, onClick handlers. */
(function () {
  "use strict";
  window.DCLogic = function () { this.props = {}; this.state = {}; };
  DCLogic.prototype.setState = function (patch) {
    Object.assign(this.state, patch);
    if (this.__render) this.__render();
  };
  var HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
  function lookup(path, scope) {
    path = path.trim();
    if (path === "true") return true;
    if (path === "false") return false;
    if (path === "null") return null;
    var parts = path.split("."), cur = scope;
    for (var i = 0; i < parts.length; i++) {
      if (cur === null || cur === undefined) return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }
  function interpolate(str, scope) {
    var whole = str.match(/^\s*\{\{\s*([^}]+?)\s*\}\}\s*$/);
    if (whole) return lookup(whole[1], scope);
    return str.replace(HOLE, function (_, p) { var v = lookup(p, scope); return v === null || v === undefined ? "" : String(v); });
  }
  function renderNodes(nodes, scope, out) {
    for (var i = 0; i < nodes.length; i++) renderNode(nodes[i], scope, out);
  }
  function renderNode(node, scope, out) {
    if (node.nodeType === 3) {
      var t = node.nodeValue;
      if (t.indexOf("{{") >= 0) t = String(interpolate(t, scope) ?? "");
      out.appendChild(document.createTextNode(t));
      return;
    }
    if (node.nodeType !== 1) return;
    var tag = node.tagName.toLowerCase();
    if (tag === "sc-if") {
      var v = interpolate(node.getAttribute("value") || "", scope);
      if (v) renderNodes(node.childNodes, scope, out);
      return;
    }
    if (tag === "sc-for") {
      var list = interpolate(node.getAttribute("list") || "", scope) || [];
      var as = node.getAttribute("as") || "item";
      for (var k = 0; k < list.length; k++) {
        var inner = Object.create(scope);
        inner[as] = list[k]; inner.$index = k;
        renderNodes(node.childNodes, inner, out);
      }
      return;
    }
    if (tag === "helmet") { renderNodes(node.childNodes, scope, out); return; }
    var TABLE_TAGS = { "x-table": "table", "x-thead": "thead", "x-tbody": "tbody", "x-tfoot": "tfoot", "x-tr": "tr", "x-th": "th", "x-td": "td" };
    var el = node.namespaceURI && node.namespaceURI !== "http://www.w3.org/1999/xhtml"
      ? document.createElementNS(node.namespaceURI, node.tagName)
      : document.createElement(TABLE_TAGS[tag] || tag);
    for (var a = 0; a < node.attributes.length; a++) {
      var attr = node.attributes[a], name = attr.name, val = attr.value;
      if (/^on[a-z]/i.test(name)) {
        var fn = interpolate(val, scope);
        if (typeof fn === "function") el.addEventListener(name.slice(2).toLowerCase(), fn);
        continue;
      }
      if (name.indexOf("hint-") === 0 || name.indexOf("data-dc") === 0) continue;
      if (val.indexOf("{{") >= 0) {
        var r = interpolate(val, scope);
        if (r === null || r === undefined || r === false) continue;
        el.setAttribute(name, r === true ? "true" : String(r));
      } else el.setAttribute(name, val);
    }
    renderNodes(node.childNodes, scope, el);
    out.appendChild(el);
  }
  function mount() {
    var tpl = document.getElementById("phil-template");
    var logic = document.getElementById("phil-logic");
    var root = document.getElementById("phil-root");
    // Table tags are renamed before parsing so <sc-for>/<sc-if> inside tables are not moved out by the HTML parser.
    var src = tpl.innerHTML.replace(/<(\/?)(table|thead|tbody|tfoot|tr|th|td)\b/gi, "<$1x-$2");
    var parsed = new DOMParser().parseFromString("<div id='tplroot'>" + src + "</div>", "text/html");
    var tplRoot = parsed.getElementById("tplroot");
    var helm = tplRoot.querySelector("helmet");
    if (helm) { var st = helm.querySelector("style"); if (st) document.head.appendChild(st.cloneNode(true)); helm.remove(); }
    var Component = new Function(logic.textContent + "\nreturn Component;")();
    var comp = new Component();
    comp.__render = function () {
      var scroller = document.getElementById("phil-dash-scroll");
      var keep = scroller ? scroller.scrollTop : 0;
      var openDetails = Array.prototype.map.call(document.querySelectorAll("details"), function (d) { return d.open; });
      var vals = comp.renderVals();
      var frag = document.createDocumentFragment();
      renderNodes(tplRoot.childNodes, vals, frag);
      root.innerHTML = "";
      root.appendChild(frag);
      var s2 = document.getElementById("phil-dash-scroll");
      if (s2) s2.scrollTop = keep;
      Array.prototype.forEach.call(document.querySelectorAll("details"), function (d, i) { if (openDetails[i]) d.open = true; });
    };
    comp.__render();
    window.__philComponent = comp;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
