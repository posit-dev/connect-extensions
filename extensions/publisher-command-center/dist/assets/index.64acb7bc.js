const p = function polyfill() {
  const relList = document.createElement("link").relList;
  if (relList && relList.supports && relList.supports("modulepreload")) {
    return;
  }
  for (const link of document.querySelectorAll('link[rel="modulepreload"]')) {
    processPreload(link);
  }
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== "childList") {
        continue;
      }
      for (const node of mutation.addedNodes) {
        if (node.tagName === "LINK" && node.rel === "modulepreload")
          processPreload(node);
      }
    }
  }).observe(document, { childList: true, subtree: true });
  function getFetchOpts(script) {
    const fetchOpts = {};
    if (script.integrity)
      fetchOpts.integrity = script.integrity;
    if (script.referrerpolicy)
      fetchOpts.referrerPolicy = script.referrerpolicy;
    if (script.crossorigin === "use-credentials")
      fetchOpts.credentials = "include";
    else if (script.crossorigin === "anonymous")
      fetchOpts.credentials = "omit";
    else
      fetchOpts.credentials = "same-origin";
    return fetchOpts;
  }
  function processPreload(link) {
    if (link.ep)
      return;
    link.ep = true;
    const fetchOpts = getFetchOpts(link);
    fetch(link.href, fetchOpts);
  }
};
p();
var commonjsGlobal = typeof globalThis !== "undefined" ? globalThis : typeof window !== "undefined" ? window : typeof global !== "undefined" ? global : typeof self !== "undefined" ? self : {};
function Vnode$7(tag, key, attrs, children, text, dom) {
  return { tag, key, attrs, children, text, dom, domSize: void 0, state: void 0, events: void 0, instance: void 0 };
}
Vnode$7.normalize = function(node) {
  if (Array.isArray(node))
    return Vnode$7("[", void 0, void 0, Vnode$7.normalizeChildren(node), void 0, void 0);
  if (node == null || typeof node === "boolean")
    return null;
  if (typeof node === "object")
    return node;
  return Vnode$7("#", void 0, void 0, String(node), void 0, void 0);
};
Vnode$7.normalizeChildren = function(input) {
  var children = [];
  if (input.length) {
    var isKeyed = input[0] != null && input[0].key != null;
    for (var i = 1; i < input.length; i++) {
      if ((input[i] != null && input[i].key != null) !== isKeyed) {
        throw new TypeError(
          isKeyed && (input[i] != null || typeof input[i] === "boolean") ? "In fragments, vnodes must either all have keys or none have keys. You may wish to consider using an explicit keyed empty fragment, m.fragment({key: ...}), instead of a hole." : "In fragments, vnodes must either all have keys or none have keys."
        );
      }
    }
    for (var i = 0; i < input.length; i++) {
      children[i] = Vnode$7.normalize(input[i]);
    }
  }
  return children;
};
var vnode = Vnode$7;
var Vnode$6 = vnode;
var hyperscriptVnode$2 = function() {
  var attrs = arguments[this], start = this + 1, children;
  if (attrs == null) {
    attrs = {};
  } else if (typeof attrs !== "object" || attrs.tag != null || Array.isArray(attrs)) {
    attrs = {};
    start = this;
  }
  if (arguments.length === start + 1) {
    children = arguments[start];
    if (!Array.isArray(children))
      children = [children];
  } else {
    children = [];
    while (start < arguments.length)
      children.push(arguments[start++]);
  }
  return Vnode$6("", attrs.key, attrs, children);
};
var hasOwn$3 = {}.hasOwnProperty;
var Vnode$5 = vnode;
var hyperscriptVnode$1 = hyperscriptVnode$2;
var hasOwn$2 = hasOwn$3;
var selectorParser = /(?:(^|#|\.)([^#\.\[\]]+))|(\[(.+?)(?:\s*=\s*("|'|)((?:\\["'\]]|.)*?)\5)?\])/g;
var selectorCache = /* @__PURE__ */ Object.create(null);
function isEmpty(object) {
  for (var key in object)
    if (hasOwn$2.call(object, key))
      return false;
  return true;
}
function compileSelector(selector) {
  var match2, tag = "div", classes = [], attrs = {};
  while (match2 = selectorParser.exec(selector)) {
    var type = match2[1], value = match2[2];
    if (type === "" && value !== "")
      tag = value;
    else if (type === "#")
      attrs.id = value;
    else if (type === ".")
      classes.push(value);
    else if (match2[3][0] === "[") {
      var attrValue = match2[6];
      if (attrValue)
        attrValue = attrValue.replace(/\\(["'])/g, "$1").replace(/\\\\/g, "\\");
      if (match2[4] === "class")
        classes.push(attrValue);
      else
        attrs[match2[4]] = attrValue === "" ? attrValue : attrValue || true;
    }
  }
  if (classes.length > 0)
    attrs.className = classes.join(" ");
  if (isEmpty(attrs))
    attrs = null;
  return selectorCache[selector] = { tag, attrs };
}
function execSelector(state, vnode2) {
  var attrs = vnode2.attrs;
  var hasClass = hasOwn$2.call(attrs, "class");
  var className = hasClass ? attrs.class : attrs.className;
  vnode2.tag = state.tag;
  if (state.attrs != null) {
    attrs = Object.assign({}, state.attrs, attrs);
    if (className != null || state.attrs.className != null)
      attrs.className = className != null ? state.attrs.className != null ? String(state.attrs.className) + " " + String(className) : className : state.attrs.className != null ? state.attrs.className : null;
  } else {
    if (className != null)
      attrs.className = className;
  }
  if (hasClass)
    attrs.class = null;
  if (state.tag === "input" && hasOwn$2.call(attrs, "type")) {
    attrs = Object.assign({ type: attrs.type }, attrs);
  }
  vnode2.attrs = attrs;
  return vnode2;
}
function hyperscript$2(selector) {
  if (selector == null || typeof selector !== "string" && typeof selector !== "function" && typeof selector.view !== "function") {
    throw Error("The selector must be either a string or a component.");
  }
  var vnode2 = hyperscriptVnode$1.apply(1, arguments);
  if (typeof selector === "string") {
    vnode2.children = Vnode$5.normalizeChildren(vnode2.children);
    if (selector !== "[")
      return execSelector(selectorCache[selector] || compileSelector(selector), vnode2);
  }
  vnode2.tag = selector;
  return vnode2;
}
var hyperscript_1$1 = hyperscript$2;
var Vnode$4 = vnode;
var trust = function(html) {
  if (html == null)
    html = "";
  return Vnode$4("<", void 0, void 0, html, void 0, void 0);
};
var Vnode$3 = vnode;
var hyperscriptVnode = hyperscriptVnode$2;
var fragment = function() {
  var vnode2 = hyperscriptVnode.apply(0, arguments);
  vnode2.tag = "[";
  vnode2.children = Vnode$3.normalizeChildren(vnode2.children);
  return vnode2;
};
var hyperscript$1 = hyperscript_1$1;
hyperscript$1.trust = trust;
hyperscript$1.fragment = fragment;
var hyperscript_1 = hyperscript$1;
var delayedRemoval$1 = /* @__PURE__ */ new WeakMap();
function* domFor$2(vnode2, object = {}) {
  var dom = vnode2.dom;
  var domSize = vnode2.domSize;
  var generation = object.generation;
  if (dom != null)
    do {
      var nextSibling = dom.nextSibling;
      if (delayedRemoval$1.get(dom) === generation) {
        yield dom;
        domSize--;
      }
      dom = nextSibling;
    } while (domSize);
}
var domFor_1 = {
  delayedRemoval: delayedRemoval$1,
  domFor: domFor$2
};
var Vnode$2 = vnode;
var df = domFor_1;
var delayedRemoval = df.delayedRemoval;
var domFor$1 = df.domFor;
var render$2 = function() {
  var nameSpace = {
    svg: "http://www.w3.org/2000/svg",
    math: "http://www.w3.org/1998/Math/MathML"
  };
  var currentRedraw;
  var currentRender;
  function getDocument(dom) {
    return dom.ownerDocument;
  }
  function getNameSpace(vnode2) {
    return vnode2.attrs && vnode2.attrs.xmlns || nameSpace[vnode2.tag];
  }
  function checkState(vnode2, original) {
    if (vnode2.state !== original)
      throw new Error("'vnode.state' must not be modified.");
  }
  function callHook(vnode2) {
    var original = vnode2.state;
    try {
      return this.apply(original, arguments);
    } finally {
      checkState(vnode2, original);
    }
  }
  function activeElement(dom) {
    try {
      return getDocument(dom).activeElement;
    } catch (e) {
      return null;
    }
  }
  function createNodes(parent, vnodes, start, end, hooks, nextSibling, ns) {
    for (var i = start; i < end; i++) {
      var vnode2 = vnodes[i];
      if (vnode2 != null) {
        createNode(parent, vnode2, hooks, ns, nextSibling);
      }
    }
  }
  function createNode(parent, vnode2, hooks, ns, nextSibling) {
    var tag = vnode2.tag;
    if (typeof tag === "string") {
      vnode2.state = {};
      if (vnode2.attrs != null)
        initLifecycle(vnode2.attrs, vnode2, hooks);
      switch (tag) {
        case "#":
          createText(parent, vnode2, nextSibling);
          break;
        case "<":
          createHTML(parent, vnode2, ns, nextSibling);
          break;
        case "[":
          createFragment(parent, vnode2, hooks, ns, nextSibling);
          break;
        default:
          createElement(parent, vnode2, hooks, ns, nextSibling);
      }
    } else
      createComponent(parent, vnode2, hooks, ns, nextSibling);
  }
  function createText(parent, vnode2, nextSibling) {
    vnode2.dom = getDocument(parent).createTextNode(vnode2.children);
    insertDOM(parent, vnode2.dom, nextSibling);
  }
  var possibleParents = { caption: "table", thead: "table", tbody: "table", tfoot: "table", tr: "tbody", th: "tr", td: "tr", colgroup: "table", col: "colgroup" };
  function createHTML(parent, vnode2, ns, nextSibling) {
    var match2 = vnode2.children.match(/^\s*?<(\w+)/im) || [];
    var temp = getDocument(parent).createElement(possibleParents[match2[1]] || "div");
    if (ns === "http://www.w3.org/2000/svg") {
      temp.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg">' + vnode2.children + "</svg>";
      temp = temp.firstChild;
    } else {
      temp.innerHTML = vnode2.children;
    }
    vnode2.dom = temp.firstChild;
    vnode2.domSize = temp.childNodes.length;
    var fragment2 = getDocument(parent).createDocumentFragment();
    var child;
    while (child = temp.firstChild) {
      fragment2.appendChild(child);
    }
    insertDOM(parent, fragment2, nextSibling);
  }
  function createFragment(parent, vnode2, hooks, ns, nextSibling) {
    var fragment2 = getDocument(parent).createDocumentFragment();
    if (vnode2.children != null) {
      var children = vnode2.children;
      createNodes(fragment2, children, 0, children.length, hooks, null, ns);
    }
    vnode2.dom = fragment2.firstChild;
    vnode2.domSize = fragment2.childNodes.length;
    insertDOM(parent, fragment2, nextSibling);
  }
  function createElement(parent, vnode2, hooks, ns, nextSibling) {
    var tag = vnode2.tag;
    var attrs = vnode2.attrs;
    var is = attrs && attrs.is;
    ns = getNameSpace(vnode2) || ns;
    var element = ns ? is ? getDocument(parent).createElementNS(ns, tag, { is }) : getDocument(parent).createElementNS(ns, tag) : is ? getDocument(parent).createElement(tag, { is }) : getDocument(parent).createElement(tag);
    vnode2.dom = element;
    if (attrs != null) {
      setAttrs(vnode2, attrs, ns);
    }
    insertDOM(parent, element, nextSibling);
    if (!maybeSetContentEditable(vnode2)) {
      if (vnode2.children != null) {
        var children = vnode2.children;
        createNodes(element, children, 0, children.length, hooks, null, ns);
        if (vnode2.tag === "select" && attrs != null)
          setLateSelectAttrs(vnode2, attrs);
      }
    }
  }
  function initComponent(vnode2, hooks) {
    var sentinel2;
    if (typeof vnode2.tag.view === "function") {
      vnode2.state = Object.create(vnode2.tag);
      sentinel2 = vnode2.state.view;
      if (sentinel2.$$reentrantLock$$ != null)
        return;
      sentinel2.$$reentrantLock$$ = true;
    } else {
      vnode2.state = void 0;
      sentinel2 = vnode2.tag;
      if (sentinel2.$$reentrantLock$$ != null)
        return;
      sentinel2.$$reentrantLock$$ = true;
      vnode2.state = vnode2.tag.prototype != null && typeof vnode2.tag.prototype.view === "function" ? new vnode2.tag(vnode2) : vnode2.tag(vnode2);
    }
    initLifecycle(vnode2.state, vnode2, hooks);
    if (vnode2.attrs != null)
      initLifecycle(vnode2.attrs, vnode2, hooks);
    vnode2.instance = Vnode$2.normalize(callHook.call(vnode2.state.view, vnode2));
    if (vnode2.instance === vnode2)
      throw Error("A view cannot return the vnode it received as argument");
    sentinel2.$$reentrantLock$$ = null;
  }
  function createComponent(parent, vnode2, hooks, ns, nextSibling) {
    initComponent(vnode2, hooks);
    if (vnode2.instance != null) {
      createNode(parent, vnode2.instance, hooks, ns, nextSibling);
      vnode2.dom = vnode2.instance.dom;
      vnode2.domSize = vnode2.dom != null ? vnode2.instance.domSize : 0;
    } else {
      vnode2.domSize = 0;
    }
  }
  function updateNodes(parent, old, vnodes, hooks, nextSibling, ns) {
    if (old === vnodes || old == null && vnodes == null)
      return;
    else if (old == null || old.length === 0)
      createNodes(parent, vnodes, 0, vnodes.length, hooks, nextSibling, ns);
    else if (vnodes == null || vnodes.length === 0)
      removeNodes(parent, old, 0, old.length);
    else {
      var isOldKeyed = old[0] != null && old[0].key != null;
      var isKeyed = vnodes[0] != null && vnodes[0].key != null;
      var start = 0, oldStart = 0;
      if (!isOldKeyed)
        while (oldStart < old.length && old[oldStart] == null)
          oldStart++;
      if (!isKeyed)
        while (start < vnodes.length && vnodes[start] == null)
          start++;
      if (isOldKeyed !== isKeyed) {
        removeNodes(parent, old, oldStart, old.length);
        createNodes(parent, vnodes, start, vnodes.length, hooks, nextSibling, ns);
      } else if (!isKeyed) {
        var commonLength = old.length < vnodes.length ? old.length : vnodes.length;
        start = start < oldStart ? start : oldStart;
        for (; start < commonLength; start++) {
          o = old[start];
          v = vnodes[start];
          if (o === v || o == null && v == null)
            continue;
          else if (o == null)
            createNode(parent, v, hooks, ns, getNextSibling(old, start + 1, nextSibling));
          else if (v == null)
            removeNode(parent, o);
          else
            updateNode(parent, o, v, hooks, getNextSibling(old, start + 1, nextSibling), ns);
        }
        if (old.length > commonLength)
          removeNodes(parent, old, start, old.length);
        if (vnodes.length > commonLength)
          createNodes(parent, vnodes, start, vnodes.length, hooks, nextSibling, ns);
      } else {
        var oldEnd = old.length - 1, end = vnodes.length - 1, map, o, v, oe, ve, topSibling;
        while (oldEnd >= oldStart && end >= start) {
          oe = old[oldEnd];
          ve = vnodes[end];
          if (oe.key !== ve.key)
            break;
          if (oe !== ve)
            updateNode(parent, oe, ve, hooks, nextSibling, ns);
          if (ve.dom != null)
            nextSibling = ve.dom;
          oldEnd--, end--;
        }
        while (oldEnd >= oldStart && end >= start) {
          o = old[oldStart];
          v = vnodes[start];
          if (o.key !== v.key)
            break;
          oldStart++, start++;
          if (o !== v)
            updateNode(parent, o, v, hooks, getNextSibling(old, oldStart, nextSibling), ns);
        }
        while (oldEnd >= oldStart && end >= start) {
          if (start === end)
            break;
          if (o.key !== ve.key || oe.key !== v.key)
            break;
          topSibling = getNextSibling(old, oldStart, nextSibling);
          moveDOM(parent, oe, topSibling);
          if (oe !== v)
            updateNode(parent, oe, v, hooks, topSibling, ns);
          if (++start <= --end)
            moveDOM(parent, o, nextSibling);
          if (o !== ve)
            updateNode(parent, o, ve, hooks, nextSibling, ns);
          if (ve.dom != null)
            nextSibling = ve.dom;
          oldStart++;
          oldEnd--;
          oe = old[oldEnd];
          ve = vnodes[end];
          o = old[oldStart];
          v = vnodes[start];
        }
        while (oldEnd >= oldStart && end >= start) {
          if (oe.key !== ve.key)
            break;
          if (oe !== ve)
            updateNode(parent, oe, ve, hooks, nextSibling, ns);
          if (ve.dom != null)
            nextSibling = ve.dom;
          oldEnd--, end--;
          oe = old[oldEnd];
          ve = vnodes[end];
        }
        if (start > end)
          removeNodes(parent, old, oldStart, oldEnd + 1);
        else if (oldStart > oldEnd)
          createNodes(parent, vnodes, start, end + 1, hooks, nextSibling, ns);
        else {
          var originalNextSibling = nextSibling, vnodesLength = end - start + 1, oldIndices = new Array(vnodesLength), li = 0, i = 0, pos = 2147483647, matched = 0, map, lisIndices;
          for (i = 0; i < vnodesLength; i++)
            oldIndices[i] = -1;
          for (i = end; i >= start; i--) {
            if (map == null)
              map = getKeyMap(old, oldStart, oldEnd + 1);
            ve = vnodes[i];
            var oldIndex = map[ve.key];
            if (oldIndex != null) {
              pos = oldIndex < pos ? oldIndex : -1;
              oldIndices[i - start] = oldIndex;
              oe = old[oldIndex];
              old[oldIndex] = null;
              if (oe !== ve)
                updateNode(parent, oe, ve, hooks, nextSibling, ns);
              if (ve.dom != null)
                nextSibling = ve.dom;
              matched++;
            }
          }
          nextSibling = originalNextSibling;
          if (matched !== oldEnd - oldStart + 1)
            removeNodes(parent, old, oldStart, oldEnd + 1);
          if (matched === 0)
            createNodes(parent, vnodes, start, end + 1, hooks, nextSibling, ns);
          else {
            if (pos === -1) {
              lisIndices = makeLisIndices(oldIndices);
              li = lisIndices.length - 1;
              for (i = end; i >= start; i--) {
                v = vnodes[i];
                if (oldIndices[i - start] === -1)
                  createNode(parent, v, hooks, ns, nextSibling);
                else {
                  if (lisIndices[li] === i - start)
                    li--;
                  else
                    moveDOM(parent, v, nextSibling);
                }
                if (v.dom != null)
                  nextSibling = vnodes[i].dom;
              }
            } else {
              for (i = end; i >= start; i--) {
                v = vnodes[i];
                if (oldIndices[i - start] === -1)
                  createNode(parent, v, hooks, ns, nextSibling);
                if (v.dom != null)
                  nextSibling = vnodes[i].dom;
              }
            }
          }
        }
      }
    }
  }
  function updateNode(parent, old, vnode2, hooks, nextSibling, ns) {
    var oldTag = old.tag, tag = vnode2.tag;
    if (oldTag === tag) {
      vnode2.state = old.state;
      vnode2.events = old.events;
      if (shouldNotUpdate(vnode2, old))
        return;
      if (typeof oldTag === "string") {
        if (vnode2.attrs != null) {
          updateLifecycle(vnode2.attrs, vnode2, hooks);
        }
        switch (oldTag) {
          case "#":
            updateText(old, vnode2);
            break;
          case "<":
            updateHTML(parent, old, vnode2, ns, nextSibling);
            break;
          case "[":
            updateFragment(parent, old, vnode2, hooks, nextSibling, ns);
            break;
          default:
            updateElement(old, vnode2, hooks, ns);
        }
      } else
        updateComponent(parent, old, vnode2, hooks, nextSibling, ns);
    } else {
      removeNode(parent, old);
      createNode(parent, vnode2, hooks, ns, nextSibling);
    }
  }
  function updateText(old, vnode2) {
    if (old.children.toString() !== vnode2.children.toString()) {
      old.dom.nodeValue = vnode2.children;
    }
    vnode2.dom = old.dom;
  }
  function updateHTML(parent, old, vnode2, ns, nextSibling) {
    if (old.children !== vnode2.children) {
      removeDOM(parent, old, void 0);
      createHTML(parent, vnode2, ns, nextSibling);
    } else {
      vnode2.dom = old.dom;
      vnode2.domSize = old.domSize;
    }
  }
  function updateFragment(parent, old, vnode2, hooks, nextSibling, ns) {
    updateNodes(parent, old.children, vnode2.children, hooks, nextSibling, ns);
    var domSize = 0, children = vnode2.children;
    vnode2.dom = null;
    if (children != null) {
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (child != null && child.dom != null) {
          if (vnode2.dom == null)
            vnode2.dom = child.dom;
          domSize += child.domSize || 1;
        }
      }
      if (domSize !== 1)
        vnode2.domSize = domSize;
    }
  }
  function updateElement(old, vnode2, hooks, ns) {
    var element = vnode2.dom = old.dom;
    ns = getNameSpace(vnode2) || ns;
    updateAttrs(vnode2, old.attrs, vnode2.attrs, ns);
    if (!maybeSetContentEditable(vnode2)) {
      updateNodes(element, old.children, vnode2.children, hooks, null, ns);
    }
  }
  function updateComponent(parent, old, vnode2, hooks, nextSibling, ns) {
    vnode2.instance = Vnode$2.normalize(callHook.call(vnode2.state.view, vnode2));
    if (vnode2.instance === vnode2)
      throw Error("A view cannot return the vnode it received as argument");
    updateLifecycle(vnode2.state, vnode2, hooks);
    if (vnode2.attrs != null)
      updateLifecycle(vnode2.attrs, vnode2, hooks);
    if (vnode2.instance != null) {
      if (old.instance == null)
        createNode(parent, vnode2.instance, hooks, ns, nextSibling);
      else
        updateNode(parent, old.instance, vnode2.instance, hooks, nextSibling, ns);
      vnode2.dom = vnode2.instance.dom;
      vnode2.domSize = vnode2.instance.domSize;
    } else if (old.instance != null) {
      removeNode(parent, old.instance);
      vnode2.dom = void 0;
      vnode2.domSize = 0;
    } else {
      vnode2.dom = old.dom;
      vnode2.domSize = old.domSize;
    }
  }
  function getKeyMap(vnodes, start, end) {
    var map = /* @__PURE__ */ Object.create(null);
    for (; start < end; start++) {
      var vnode2 = vnodes[start];
      if (vnode2 != null) {
        var key = vnode2.key;
        if (key != null)
          map[key] = start;
      }
    }
    return map;
  }
  var lisTemp = [];
  function makeLisIndices(a) {
    var result = [0];
    var u = 0, v = 0, i = 0;
    var il = lisTemp.length = a.length;
    for (var i = 0; i < il; i++)
      lisTemp[i] = a[i];
    for (var i = 0; i < il; ++i) {
      if (a[i] === -1)
        continue;
      var j = result[result.length - 1];
      if (a[j] < a[i]) {
        lisTemp[i] = j;
        result.push(i);
        continue;
      }
      u = 0;
      v = result.length - 1;
      while (u < v) {
        var c = (u >>> 1) + (v >>> 1) + (u & v & 1);
        if (a[result[c]] < a[i]) {
          u = c + 1;
        } else {
          v = c;
        }
      }
      if (a[i] < a[result[u]]) {
        if (u > 0)
          lisTemp[i] = result[u - 1];
        result[u] = i;
      }
    }
    u = result.length;
    v = result[u - 1];
    while (u-- > 0) {
      result[u] = v;
      v = lisTemp[v];
    }
    lisTemp.length = 0;
    return result;
  }
  function getNextSibling(vnodes, i, nextSibling) {
    for (; i < vnodes.length; i++) {
      if (vnodes[i] != null && vnodes[i].dom != null)
        return vnodes[i].dom;
    }
    return nextSibling;
  }
  function moveDOM(parent, vnode2, nextSibling) {
    if (vnode2.dom != null) {
      var target;
      if (vnode2.domSize == null) {
        target = vnode2.dom;
      } else {
        target = getDocument(parent).createDocumentFragment();
        for (var dom of domFor$1(vnode2))
          target.appendChild(dom);
      }
      insertDOM(parent, target, nextSibling);
    }
  }
  function insertDOM(parent, dom, nextSibling) {
    if (nextSibling != null)
      parent.insertBefore(dom, nextSibling);
    else
      parent.appendChild(dom);
  }
  function maybeSetContentEditable(vnode2) {
    if (vnode2.attrs == null || vnode2.attrs.contenteditable == null && vnode2.attrs.contentEditable == null)
      return false;
    var children = vnode2.children;
    if (children != null && children.length === 1 && children[0].tag === "<") {
      var content = children[0].children;
      if (vnode2.dom.innerHTML !== content)
        vnode2.dom.innerHTML = content;
    } else if (children != null && children.length !== 0)
      throw new Error("Child node of a contenteditable must be trusted.");
    return true;
  }
  function removeNodes(parent, vnodes, start, end) {
    for (var i = start; i < end; i++) {
      var vnode2 = vnodes[i];
      if (vnode2 != null)
        removeNode(parent, vnode2);
    }
  }
  function removeNode(parent, vnode2) {
    var mask = 0;
    var original = vnode2.state;
    var stateResult, attrsResult;
    if (typeof vnode2.tag !== "string" && typeof vnode2.state.onbeforeremove === "function") {
      var result = callHook.call(vnode2.state.onbeforeremove, vnode2);
      if (result != null && typeof result.then === "function") {
        mask = 1;
        stateResult = result;
      }
    }
    if (vnode2.attrs && typeof vnode2.attrs.onbeforeremove === "function") {
      var result = callHook.call(vnode2.attrs.onbeforeremove, vnode2);
      if (result != null && typeof result.then === "function") {
        mask |= 2;
        attrsResult = result;
      }
    }
    checkState(vnode2, original);
    var generation;
    if (!mask) {
      onremove(vnode2);
      removeDOM(parent, vnode2, generation);
    } else {
      generation = currentRender;
      for (var dom of domFor$1(vnode2))
        delayedRemoval.set(dom, generation);
      if (stateResult != null) {
        stateResult.finally(function() {
          if (mask & 1) {
            mask &= 2;
            if (!mask) {
              checkState(vnode2, original);
              onremove(vnode2);
              removeDOM(parent, vnode2, generation);
            }
          }
        });
      }
      if (attrsResult != null) {
        attrsResult.finally(function() {
          if (mask & 2) {
            mask &= 1;
            if (!mask) {
              checkState(vnode2, original);
              onremove(vnode2);
              removeDOM(parent, vnode2, generation);
            }
          }
        });
      }
    }
  }
  function removeDOM(parent, vnode2, generation) {
    if (vnode2.dom == null)
      return;
    if (vnode2.domSize == null) {
      if (delayedRemoval.get(vnode2.dom) === generation)
        parent.removeChild(vnode2.dom);
    } else {
      for (var dom of domFor$1(vnode2, { generation }))
        parent.removeChild(dom);
    }
  }
  function onremove(vnode2) {
    if (typeof vnode2.tag !== "string" && typeof vnode2.state.onremove === "function")
      callHook.call(vnode2.state.onremove, vnode2);
    if (vnode2.attrs && typeof vnode2.attrs.onremove === "function")
      callHook.call(vnode2.attrs.onremove, vnode2);
    if (typeof vnode2.tag !== "string") {
      if (vnode2.instance != null)
        onremove(vnode2.instance);
    } else {
      var children = vnode2.children;
      if (Array.isArray(children)) {
        for (var i = 0; i < children.length; i++) {
          var child = children[i];
          if (child != null)
            onremove(child);
        }
      }
    }
  }
  function setAttrs(vnode2, attrs, ns) {
    for (var key in attrs) {
      setAttr(vnode2, key, null, attrs[key], ns);
    }
  }
  function setAttr(vnode2, key, old, value, ns) {
    if (key === "key" || key === "is" || value == null || isLifecycleMethod(key) || old === value && !isFormAttribute(vnode2, key) && typeof value !== "object")
      return;
    if (key[0] === "o" && key[1] === "n")
      return updateEvent(vnode2, key, value);
    if (key.slice(0, 6) === "xlink:")
      vnode2.dom.setAttributeNS("http://www.w3.org/1999/xlink", key.slice(6), value);
    else if (key === "style")
      updateStyle(vnode2.dom, old, value);
    else if (hasPropertyKey(vnode2, key, ns)) {
      if (key === "value") {
        var isFileInput = vnode2.tag === "input" && vnode2.attrs.type === "file";
        if ((vnode2.tag === "input" || vnode2.tag === "textarea") && vnode2.dom.value === "" + value && (isFileInput || vnode2.dom === activeElement(vnode2.dom)))
          return;
        if (vnode2.tag === "select" && old !== null && vnode2.dom.value === "" + value)
          return;
        if (vnode2.tag === "option" && old !== null && vnode2.dom.value === "" + value)
          return;
        if (isFileInput && "" + value !== "") {
          console.error("`value` is read-only on file inputs!");
          return;
        }
      }
      if (vnode2.tag === "input" && key === "type")
        vnode2.dom.setAttribute(key, value);
      else
        vnode2.dom[key] = value;
    } else {
      if (typeof value === "boolean") {
        if (value)
          vnode2.dom.setAttribute(key, "");
        else
          vnode2.dom.removeAttribute(key);
      } else
        vnode2.dom.setAttribute(key === "className" ? "class" : key, value);
    }
  }
  function removeAttr(vnode2, key, old, ns) {
    if (key === "key" || key === "is" || old == null || isLifecycleMethod(key))
      return;
    if (key[0] === "o" && key[1] === "n")
      updateEvent(vnode2, key, void 0);
    else if (key === "style")
      updateStyle(vnode2.dom, old, null);
    else if (hasPropertyKey(vnode2, key, ns) && key !== "className" && key !== "title" && !(key === "value" && (vnode2.tag === "option" || vnode2.tag === "select" && vnode2.dom.selectedIndex === -1 && vnode2.dom === activeElement(vnode2.dom))) && !(vnode2.tag === "input" && key === "type")) {
      vnode2.dom[key] = null;
    } else {
      var nsLastIndex = key.indexOf(":");
      if (nsLastIndex !== -1)
        key = key.slice(nsLastIndex + 1);
      if (old !== false)
        vnode2.dom.removeAttribute(key === "className" ? "class" : key);
    }
  }
  function setLateSelectAttrs(vnode2, attrs) {
    if ("value" in attrs) {
      if (attrs.value === null) {
        if (vnode2.dom.selectedIndex !== -1)
          vnode2.dom.value = null;
      } else {
        var normalized = "" + attrs.value;
        if (vnode2.dom.value !== normalized || vnode2.dom.selectedIndex === -1) {
          vnode2.dom.value = normalized;
        }
      }
    }
    if ("selectedIndex" in attrs)
      setAttr(vnode2, "selectedIndex", null, attrs.selectedIndex, void 0);
  }
  function updateAttrs(vnode2, old, attrs, ns) {
    if (old && old === attrs) {
      console.warn("Don't reuse attrs object, use new object for every redraw, this will throw in next major");
    }
    if (attrs != null) {
      for (var key in attrs) {
        setAttr(vnode2, key, old && old[key], attrs[key], ns);
      }
    }
    var val;
    if (old != null) {
      for (var key in old) {
        if ((val = old[key]) != null && (attrs == null || attrs[key] == null)) {
          removeAttr(vnode2, key, val, ns);
        }
      }
    }
  }
  function isFormAttribute(vnode2, attr) {
    return attr === "value" || attr === "checked" || attr === "selectedIndex" || attr === "selected" && vnode2.dom === activeElement(vnode2.dom) || vnode2.tag === "option" && vnode2.dom.parentNode === activeElement(vnode2.dom);
  }
  function isLifecycleMethod(attr) {
    return attr === "oninit" || attr === "oncreate" || attr === "onupdate" || attr === "onremove" || attr === "onbeforeremove" || attr === "onbeforeupdate";
  }
  function hasPropertyKey(vnode2, key, ns) {
    return ns === void 0 && (vnode2.tag.indexOf("-") > -1 || vnode2.attrs != null && vnode2.attrs.is || key !== "href" && key !== "list" && key !== "form" && key !== "width" && key !== "height") && key in vnode2.dom;
  }
  function updateStyle(element, old, style) {
    if (old === style)
      ;
    else if (style == null) {
      element.style = "";
    } else if (typeof style !== "object") {
      element.style = style;
    } else if (old == null || typeof old !== "object") {
      element.style.cssText = "";
      for (var key in style) {
        var value = style[key];
        if (value != null) {
          if (key.includes("-"))
            element.style.setProperty(key, String(value));
          else
            element.style[key] = String(value);
        }
      }
    } else {
      for (var key in style) {
        var value = style[key];
        if (value != null && (value = String(value)) !== String(old[key])) {
          if (key.includes("-"))
            element.style.setProperty(key, value);
          else
            element.style[key] = value;
        }
      }
      for (var key in old) {
        if (old[key] != null && style[key] == null) {
          if (key.includes("-"))
            element.style.removeProperty(key);
          else
            element.style[key] = "";
        }
      }
    }
  }
  function EventDict() {
    this._ = currentRedraw;
  }
  EventDict.prototype = /* @__PURE__ */ Object.create(null);
  EventDict.prototype.handleEvent = function(ev) {
    var handler = this["on" + ev.type];
    var result;
    if (typeof handler === "function")
      result = handler.call(ev.currentTarget, ev);
    else if (typeof handler.handleEvent === "function")
      handler.handleEvent(ev);
    if (this._ && ev.redraw !== false)
      (0, this._)();
    if (result === false) {
      ev.preventDefault();
      ev.stopPropagation();
    }
  };
  function updateEvent(vnode2, key, value) {
    if (vnode2.events != null) {
      vnode2.events._ = currentRedraw;
      if (vnode2.events[key] === value)
        return;
      if (value != null && (typeof value === "function" || typeof value === "object")) {
        if (vnode2.events[key] == null)
          vnode2.dom.addEventListener(key.slice(2), vnode2.events, false);
        vnode2.events[key] = value;
      } else {
        if (vnode2.events[key] != null)
          vnode2.dom.removeEventListener(key.slice(2), vnode2.events, false);
        vnode2.events[key] = void 0;
      }
    } else if (value != null && (typeof value === "function" || typeof value === "object")) {
      vnode2.events = new EventDict();
      vnode2.dom.addEventListener(key.slice(2), vnode2.events, false);
      vnode2.events[key] = value;
    }
  }
  function initLifecycle(source, vnode2, hooks) {
    if (typeof source.oninit === "function")
      callHook.call(source.oninit, vnode2);
    if (typeof source.oncreate === "function")
      hooks.push(callHook.bind(source.oncreate, vnode2));
  }
  function updateLifecycle(source, vnode2, hooks) {
    if (typeof source.onupdate === "function")
      hooks.push(callHook.bind(source.onupdate, vnode2));
  }
  function shouldNotUpdate(vnode2, old) {
    do {
      if (vnode2.attrs != null && typeof vnode2.attrs.onbeforeupdate === "function") {
        var force = callHook.call(vnode2.attrs.onbeforeupdate, vnode2, old);
        if (force !== void 0 && !force)
          break;
      }
      if (typeof vnode2.tag !== "string" && typeof vnode2.state.onbeforeupdate === "function") {
        var force = callHook.call(vnode2.state.onbeforeupdate, vnode2, old);
        if (force !== void 0 && !force)
          break;
      }
      return false;
    } while (false);
    vnode2.dom = old.dom;
    vnode2.domSize = old.domSize;
    vnode2.instance = old.instance;
    vnode2.attrs = old.attrs;
    vnode2.children = old.children;
    vnode2.text = old.text;
    return true;
  }
  var currentDOM;
  return function(dom, vnodes, redraw) {
    if (!dom)
      throw new TypeError("DOM element being rendered to does not exist.");
    if (currentDOM != null && dom.contains(currentDOM)) {
      throw new TypeError("Node is currently being rendered to and thus is locked.");
    }
    var prevRedraw = currentRedraw;
    var prevDOM = currentDOM;
    var hooks = [];
    var active = activeElement(dom);
    var namespace = dom.namespaceURI;
    currentDOM = dom;
    currentRedraw = typeof redraw === "function" ? redraw : void 0;
    currentRender = {};
    try {
      if (dom.vnodes == null)
        dom.textContent = "";
      vnodes = Vnode$2.normalizeChildren(Array.isArray(vnodes) ? vnodes : [vnodes]);
      updateNodes(dom, dom.vnodes, vnodes, hooks, null, namespace === "http://www.w3.org/1999/xhtml" ? void 0 : namespace);
      dom.vnodes = vnodes;
      if (active != null && activeElement(dom) !== active && typeof active.focus === "function")
        active.focus();
      for (var i = 0; i < hooks.length; i++)
        hooks[i]();
    } finally {
      currentRedraw = prevRedraw;
      currentDOM = prevDOM;
    }
  };
};
var render$1 = render$2();
var Vnode$1 = vnode;
var mountRedraw$4 = function(render2, schedule, console2) {
  var subscriptions = [];
  var pending = false;
  var offset = -1;
  function sync() {
    for (offset = 0; offset < subscriptions.length; offset += 2) {
      try {
        render2(subscriptions[offset], Vnode$1(subscriptions[offset + 1]), redraw);
      } catch (e) {
        console2.error(e);
      }
    }
    offset = -1;
  }
  function redraw() {
    if (!pending) {
      pending = true;
      schedule(function() {
        pending = false;
        sync();
      });
    }
  }
  redraw.sync = sync;
  function mount(root2, component) {
    if (component != null && component.view == null && typeof component !== "function") {
      throw new TypeError("m.mount expects a component, not a vnode.");
    }
    var index2 = subscriptions.indexOf(root2);
    if (index2 >= 0) {
      subscriptions.splice(index2, 2);
      if (index2 <= offset)
        offset -= 2;
      render2(root2, []);
    }
    if (component != null) {
      subscriptions.push(root2, component);
      render2(root2, Vnode$1(component), redraw);
    }
  }
  return { mount, redraw };
};
var render = render$1;
var mountRedraw$3 = mountRedraw$4(render, typeof requestAnimationFrame !== "undefined" ? requestAnimationFrame : null, typeof console !== "undefined" ? console : null);
var build$1 = function(object) {
  if (Object.prototype.toString.call(object) !== "[object Object]")
    return "";
  var args = [];
  for (var key in object) {
    destructure(key, object[key]);
  }
  return args.join("&");
  function destructure(key2, value) {
    if (Array.isArray(value)) {
      for (var i = 0; i < value.length; i++) {
        destructure(key2 + "[" + i + "]", value[i]);
      }
    } else if (Object.prototype.toString.call(value) === "[object Object]") {
      for (var i in value) {
        destructure(key2 + "[" + i + "]", value[i]);
      }
    } else
      args.push(encodeURIComponent(key2) + (value != null && value !== "" ? "=" + encodeURIComponent(value) : ""));
  }
};
var buildQueryString = build$1;
var build = function(template, params) {
  if (/:([^\/\.-]+)(\.{3})?:/.test(template)) {
    throw new SyntaxError("Template parameter names must be separated by either a '/', '-', or '.'.");
  }
  if (params == null)
    return template;
  var queryIndex = template.indexOf("?");
  var hashIndex = template.indexOf("#");
  var queryEnd = hashIndex < 0 ? template.length : hashIndex;
  var pathEnd = queryIndex < 0 ? queryEnd : queryIndex;
  var path = template.slice(0, pathEnd);
  var query = {};
  Object.assign(query, params);
  var resolved = path.replace(/:([^\/\.-]+)(\.{3})?/g, function(m3, key, variadic) {
    delete query[key];
    if (params[key] == null)
      return m3;
    return variadic ? params[key] : encodeURIComponent(String(params[key]));
  });
  var newQueryIndex = resolved.indexOf("?");
  var newHashIndex = resolved.indexOf("#");
  var newQueryEnd = newHashIndex < 0 ? resolved.length : newHashIndex;
  var newPathEnd = newQueryIndex < 0 ? newQueryEnd : newQueryIndex;
  var result = resolved.slice(0, newPathEnd);
  if (queryIndex >= 0)
    result += template.slice(queryIndex, queryEnd);
  if (newQueryIndex >= 0)
    result += (queryIndex < 0 ? "?" : "&") + resolved.slice(newQueryIndex, newQueryEnd);
  var querystring = buildQueryString(query);
  if (querystring)
    result += (queryIndex < 0 && newQueryIndex < 0 ? "?" : "&") + querystring;
  if (hashIndex >= 0)
    result += template.slice(hashIndex);
  if (newHashIndex >= 0)
    result += (hashIndex < 0 ? "" : "&") + resolved.slice(newHashIndex);
  return result;
};
var buildPathname$1 = build;
var hasOwn$1 = hasOwn$3;
var request$2 = function($window, oncompletion) {
  function PromiseProxy(executor) {
    return new Promise(executor);
  }
  function makeRequest(url, args) {
    return new Promise(function(resolve, reject) {
      url = buildPathname$1(url, args.params);
      var method = args.method != null ? args.method.toUpperCase() : "GET";
      var body = args.body;
      var assumeJSON = (args.serialize == null || args.serialize === JSON.serialize) && !(body instanceof $window.FormData || body instanceof $window.URLSearchParams);
      var responseType = args.responseType || (typeof args.extract === "function" ? "" : "json");
      var xhr = new $window.XMLHttpRequest(), aborted = false, isTimeout = false;
      var original = xhr, replacedAbort;
      var abort = xhr.abort;
      xhr.abort = function() {
        aborted = true;
        abort.call(this);
      };
      xhr.open(method, url, args.async !== false, typeof args.user === "string" ? args.user : void 0, typeof args.password === "string" ? args.password : void 0);
      if (assumeJSON && body != null && !hasHeader(args, "content-type")) {
        xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
      }
      if (typeof args.deserialize !== "function" && !hasHeader(args, "accept")) {
        xhr.setRequestHeader("Accept", "application/json, text/*");
      }
      if (args.withCredentials)
        xhr.withCredentials = args.withCredentials;
      if (args.timeout)
        xhr.timeout = args.timeout;
      xhr.responseType = responseType;
      for (var key in args.headers) {
        if (hasOwn$1.call(args.headers, key)) {
          xhr.setRequestHeader(key, args.headers[key]);
        }
      }
      xhr.onreadystatechange = function(ev) {
        if (aborted)
          return;
        if (ev.target.readyState === 4) {
          try {
            var success = ev.target.status >= 200 && ev.target.status < 300 || ev.target.status === 304 || /^file:\/\//i.test(url);
            var response = ev.target.response, message2;
            if (responseType === "json") {
              if (!ev.target.responseType && typeof args.extract !== "function") {
                try {
                  response = JSON.parse(ev.target.responseText);
                } catch (e) {
                  response = null;
                }
              }
            } else if (!responseType || responseType === "text") {
              if (response == null)
                response = ev.target.responseText;
            }
            if (typeof args.extract === "function") {
              response = args.extract(ev.target, args);
              success = true;
            } else if (typeof args.deserialize === "function") {
              response = args.deserialize(response);
            }
            if (success) {
              if (typeof args.type === "function") {
                if (Array.isArray(response)) {
                  for (var i = 0; i < response.length; i++) {
                    response[i] = new args.type(response[i]);
                  }
                } else
                  response = new args.type(response);
              }
              resolve(response);
            } else {
              var completeErrorResponse = function() {
                try {
                  message2 = ev.target.responseText;
                } catch (e) {
                  message2 = response;
                }
                var error = new Error(message2);
                error.code = ev.target.status;
                error.response = response;
                reject(error);
              };
              if (xhr.status === 0) {
                setTimeout(function() {
                  if (isTimeout)
                    return;
                  completeErrorResponse();
                });
              } else
                completeErrorResponse();
            }
          } catch (e) {
            reject(e);
          }
        }
      };
      xhr.ontimeout = function(ev) {
        isTimeout = true;
        var error = new Error("Request timed out");
        error.code = ev.target.status;
        reject(error);
      };
      if (typeof args.config === "function") {
        xhr = args.config(xhr, args, url) || xhr;
        if (xhr !== original) {
          replacedAbort = xhr.abort;
          xhr.abort = function() {
            aborted = true;
            replacedAbort.call(this);
          };
        }
      }
      if (body == null)
        xhr.send();
      else if (typeof args.serialize === "function")
        xhr.send(args.serialize(body));
      else if (body instanceof $window.FormData || body instanceof $window.URLSearchParams)
        xhr.send(body);
      else
        xhr.send(JSON.stringify(body));
    });
  }
  PromiseProxy.prototype = Promise.prototype;
  PromiseProxy.__proto__ = Promise;
  function hasHeader(args, name) {
    for (var key in args.headers) {
      if (hasOwn$1.call(args.headers, key) && key.toLowerCase() === name)
        return true;
    }
    return false;
  }
  return {
    request: function(url, args) {
      if (typeof url !== "string") {
        args = url;
        url = url.url;
      } else if (args == null)
        args = {};
      var promise = makeRequest(url, args);
      if (args.background === true)
        return promise;
      var count = 0;
      function complete() {
        if (--count === 0 && typeof oncompletion === "function")
          oncompletion();
      }
      return wrap(promise);
      function wrap(promise2) {
        var then = promise2.then;
        promise2.constructor = PromiseProxy;
        promise2.then = function() {
          count++;
          var next = then.apply(promise2, arguments);
          next.then(complete, function(e) {
            complete();
            if (count === 0)
              throw e;
          });
          return wrap(next);
        };
        return promise2;
      }
    }
  };
};
var mountRedraw$2 = mountRedraw$3;
var request$1 = request$2(typeof window !== "undefined" ? window : null, mountRedraw$2.redraw);
function decodeURIComponentSave$1(str) {
  try {
    return decodeURIComponent(str);
  } catch (err) {
    return str;
  }
}
var parse$1 = function(string) {
  if (string === "" || string == null)
    return {};
  if (string.charAt(0) === "?")
    string = string.slice(1);
  var entries = string.split("&"), counters = {}, data = {};
  for (var i = 0; i < entries.length; i++) {
    var entry = entries[i].split("=");
    var key = decodeURIComponentSave$1(entry[0]);
    var value = entry.length === 2 ? decodeURIComponentSave$1(entry[1]) : "";
    if (value === "true")
      value = true;
    else if (value === "false")
      value = false;
    var levels = key.split(/\]\[?|\[/);
    var cursor = data;
    if (key.indexOf("[") > -1)
      levels.pop();
    for (var j = 0; j < levels.length; j++) {
      var level = levels[j], nextLevel = levels[j + 1];
      var isNumber = nextLevel == "" || !isNaN(parseInt(nextLevel, 10));
      if (level === "") {
        var key = levels.slice(0, j).join();
        if (counters[key] == null) {
          counters[key] = Array.isArray(cursor) ? cursor.length : 0;
        }
        level = counters[key]++;
      } else if (level === "__proto__")
        break;
      if (j === levels.length - 1)
        cursor[level] = value;
      else {
        var desc = Object.getOwnPropertyDescriptor(cursor, level);
        if (desc != null)
          desc = desc.value;
        if (desc == null)
          cursor[level] = desc = isNumber ? [] : {};
        cursor = desc;
      }
    }
  }
  return data;
};
var parseQueryString = parse$1;
var parse = function(url) {
  var queryIndex = url.indexOf("?");
  var hashIndex = url.indexOf("#");
  var queryEnd = hashIndex < 0 ? url.length : hashIndex;
  var pathEnd = queryIndex < 0 ? queryEnd : queryIndex;
  var path = url.slice(0, pathEnd).replace(/\/{2,}/g, "/");
  if (!path)
    path = "/";
  else {
    if (path[0] !== "/")
      path = "/" + path;
  }
  return {
    path,
    params: queryIndex < 0 ? {} : parseQueryString(url.slice(queryIndex + 1, queryEnd))
  };
};
var parsePathname$1 = parse;
var compileTemplate$1 = function(template) {
  var templateData = parsePathname$1(template);
  var templateKeys = Object.keys(templateData.params);
  var keys = [];
  var regexp = new RegExp("^" + templateData.path.replace(
    /:([^\/.-]+)(\.{3}|\.(?!\.)|-)?|[\\^$*+.()|\[\]{}]/g,
    function(m3, key, extra) {
      if (key == null)
        return "\\" + m3;
      keys.push({ k: key, r: extra === "..." });
      if (extra === "...")
        return "(.*)";
      if (extra === ".")
        return "([^/]+)\\.";
      return "([^/]+)" + (extra || "");
    }
  ) + "$");
  return function(data) {
    for (var i = 0; i < templateKeys.length; i++) {
      if (templateData.params[templateKeys[i]] !== data.params[templateKeys[i]])
        return false;
    }
    if (!keys.length)
      return regexp.test(data.path);
    var values = regexp.exec(data.path);
    if (values == null)
      return false;
    for (var i = 0; i < keys.length; i++) {
      data.params[keys[i].k] = keys[i].r ? values[i + 1] : decodeURIComponent(values[i + 1]);
    }
    return true;
  };
};
var hasOwn = hasOwn$3;
var magic = new RegExp("^(?:key|oninit|oncreate|onbeforeupdate|onupdate|onbeforeremove|onremove)$");
var censor$1 = function(attrs, extras) {
  var result = {};
  if (extras != null) {
    for (var key in attrs) {
      if (hasOwn.call(attrs, key) && !magic.test(key) && extras.indexOf(key) < 0) {
        result[key] = attrs[key];
      }
    }
  } else {
    for (var key in attrs) {
      if (hasOwn.call(attrs, key) && !magic.test(key)) {
        result[key] = attrs[key];
      }
    }
  }
  return result;
};
var Vnode = vnode;
var m$1 = hyperscript_1$1;
var buildPathname = build;
var parsePathname = parse;
var compileTemplate = compileTemplate$1;
var censor = censor$1;
var sentinel = {};
function decodeURIComponentSave(component) {
  try {
    return decodeURIComponent(component);
  } catch (e) {
    return component;
  }
}
var router = function($window, mountRedraw2) {
  var callAsync = $window == null ? null : typeof $window.setImmediate === "function" ? $window.setImmediate : $window.setTimeout;
  var p2 = Promise.resolve();
  var scheduled = false;
  var ready = false;
  var state = 0;
  var compiled, fallbackRoute;
  var currentResolver = sentinel, component, attrs, currentPath, lastUpdate;
  var RouterRoot = {
    onbeforeupdate: function() {
      state = state ? 2 : 1;
      return !(!state || sentinel === currentResolver);
    },
    onremove: function() {
      $window.removeEventListener("popstate", fireAsync, false);
      $window.removeEventListener("hashchange", resolveRoute, false);
    },
    view: function() {
      if (!state || sentinel === currentResolver)
        return;
      var vnode2 = [Vnode(component, attrs.key, attrs)];
      if (currentResolver)
        vnode2 = currentResolver.render(vnode2[0]);
      return vnode2;
    }
  };
  var SKIP = route2.SKIP = {};
  function resolveRoute() {
    scheduled = false;
    var prefix = $window.location.hash;
    if (route2.prefix[0] !== "#") {
      prefix = $window.location.search + prefix;
      if (route2.prefix[0] !== "?") {
        prefix = $window.location.pathname + prefix;
        if (prefix[0] !== "/")
          prefix = "/" + prefix;
      }
    }
    var path = prefix.concat().replace(/(?:%[a-f89][a-f0-9])+/gim, decodeURIComponentSave).slice(route2.prefix.length);
    var data = parsePathname(path);
    Object.assign(data.params, $window.history.state);
    function reject(e) {
      console.error(e);
      setPath(fallbackRoute, null, { replace: true });
    }
    loop(0);
    function loop(i) {
      for (; i < compiled.length; i++) {
        if (compiled[i].check(data)) {
          var payload = compiled[i].component;
          var matchedRoute = compiled[i].route;
          var localComp = payload;
          var update = lastUpdate = function(comp) {
            if (update !== lastUpdate)
              return;
            if (comp === SKIP)
              return loop(i + 1);
            component = comp != null && (typeof comp.view === "function" || typeof comp === "function") ? comp : "div";
            attrs = data.params, currentPath = path, lastUpdate = null;
            currentResolver = payload.render ? payload : null;
            if (state === 2)
              mountRedraw2.redraw();
            else {
              state = 2;
              mountRedraw2.redraw.sync();
            }
          };
          if (payload.view || typeof payload === "function") {
            payload = {};
            update(localComp);
          } else if (payload.onmatch) {
            p2.then(function() {
              return payload.onmatch(data.params, path, matchedRoute);
            }).then(update, path === fallbackRoute ? null : reject);
          } else
            update("div");
          return;
        }
      }
      if (path === fallbackRoute) {
        throw new Error("Could not resolve default route " + fallbackRoute + ".");
      }
      setPath(fallbackRoute, null, { replace: true });
    }
  }
  function fireAsync() {
    if (!scheduled) {
      scheduled = true;
      callAsync(resolveRoute);
    }
  }
  function setPath(path, data, options) {
    path = buildPathname(path, data);
    if (ready) {
      fireAsync();
      var state2 = options ? options.state : null;
      var title = options ? options.title : null;
      if (options && options.replace)
        $window.history.replaceState(state2, title, route2.prefix + path);
      else
        $window.history.pushState(state2, title, route2.prefix + path);
    } else {
      $window.location.href = route2.prefix + path;
    }
  }
  function route2(root2, defaultRoute, routes) {
    if (!root2)
      throw new TypeError("DOM element being rendered to does not exist.");
    compiled = Object.keys(routes).map(function(route3) {
      if (route3[0] !== "/")
        throw new SyntaxError("Routes must start with a '/'.");
      if (/:([^\/\.-]+)(\.{3})?:/.test(route3)) {
        throw new SyntaxError("Route parameter names must be separated with either '/', '.', or '-'.");
      }
      return {
        route: route3,
        component: routes[route3],
        check: compileTemplate(route3)
      };
    });
    fallbackRoute = defaultRoute;
    if (defaultRoute != null) {
      var defaultData = parsePathname(defaultRoute);
      if (!compiled.some(function(i) {
        return i.check(defaultData);
      })) {
        throw new ReferenceError("Default route doesn't match any known routes.");
      }
    }
    if (typeof $window.history.pushState === "function") {
      $window.addEventListener("popstate", fireAsync, false);
    } else if (route2.prefix[0] === "#") {
      $window.addEventListener("hashchange", resolveRoute, false);
    }
    ready = true;
    mountRedraw2.mount(root2, RouterRoot);
    resolveRoute();
  }
  route2.set = function(path, data, options) {
    if (lastUpdate != null) {
      options = options || {};
      options.replace = true;
    }
    lastUpdate = null;
    setPath(path, data, options);
  };
  route2.get = function() {
    return currentPath;
  };
  route2.prefix = "#!";
  route2.Link = {
    view: function(vnode2) {
      var child = m$1(
        vnode2.attrs.selector || "a",
        censor(vnode2.attrs, ["options", "params", "selector", "onclick"]),
        vnode2.children
      );
      var options, onclick, href;
      if (child.attrs.disabled = Boolean(child.attrs.disabled)) {
        child.attrs.href = null;
        child.attrs["aria-disabled"] = "true";
      } else {
        options = vnode2.attrs.options;
        onclick = vnode2.attrs.onclick;
        href = buildPathname(child.attrs.href, vnode2.attrs.params);
        child.attrs.href = route2.prefix + href;
        child.attrs.onclick = function(e) {
          var result;
          if (typeof onclick === "function") {
            result = onclick.call(e.currentTarget, e);
          } else if (onclick == null || typeof onclick !== "object")
            ;
          else if (typeof onclick.handleEvent === "function") {
            onclick.handleEvent(e);
          }
          if (result !== false && !e.defaultPrevented && (e.button === 0 || e.which === 0 || e.which === 1) && (!e.currentTarget.target || e.currentTarget.target === "_self") && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey) {
            e.preventDefault();
            e.redraw = false;
            route2.set(href, null, options);
          }
        };
      }
      return child;
    }
  };
  route2.param = function(key) {
    return attrs && key != null ? attrs[key] : attrs;
  };
  return route2;
};
var mountRedraw$1 = mountRedraw$3;
var route = router(typeof window !== "undefined" ? window : null, mountRedraw$1);
var hyperscript = hyperscript_1;
var request = request$1;
var mountRedraw = mountRedraw$3;
var domFor = domFor_1;
var m = function m2() {
  return hyperscript.apply(this, arguments);
};
m.m = hyperscript;
m.trust = hyperscript.trust;
m.fragment = hyperscript.fragment;
m.Fragment = "[";
m.mount = mountRedraw.mount;
m.route = route;
m.render = render$1;
m.redraw = mountRedraw.redraw;
m.request = request.request;
m.parseQueryString = parse$1;
m.buildQueryString = build$1;
m.parsePathname = parse;
m.buildPathname = build;
m.vnode = vnode;
m.censor = censor$1;
m.domFor = domFor.domFor;
var mithril = m;
var bootstrap_bundle_min = { exports: {} };
/*!
  * Bootstrap v5.3.3 (https://getbootstrap.com/)
  * Copyright 2011-2024 The Bootstrap Authors (https://github.com/twbs/bootstrap/graphs/contributors)
  * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
  */
(function(module, exports) {
  !function(t, e) {
    module.exports = e();
  }(commonjsGlobal, function() {
    const t = /* @__PURE__ */ new Map(), e = { set(e2, i2, n2) {
      t.has(e2) || t.set(e2, /* @__PURE__ */ new Map());
      const s2 = t.get(e2);
      s2.has(i2) || 0 === s2.size ? s2.set(i2, n2) : console.error(`Bootstrap doesn't allow more than one instance per element. Bound instance: ${Array.from(s2.keys())[0]}.`);
    }, get: (e2, i2) => t.has(e2) && t.get(e2).get(i2) || null, remove(e2, i2) {
      if (!t.has(e2))
        return;
      const n2 = t.get(e2);
      n2.delete(i2), 0 === n2.size && t.delete(e2);
    } }, i = "transitionend", n = (t2) => (t2 && window.CSS && window.CSS.escape && (t2 = t2.replace(/#([^\s"#']+)/g, (t3, e2) => `#${CSS.escape(e2)}`)), t2), s = (t2) => {
      t2.dispatchEvent(new Event(i));
    }, o = (t2) => !(!t2 || "object" != typeof t2) && (void 0 !== t2.jquery && (t2 = t2[0]), void 0 !== t2.nodeType), r = (t2) => o(t2) ? t2.jquery ? t2[0] : t2 : "string" == typeof t2 && t2.length > 0 ? document.querySelector(n(t2)) : null, a = (t2) => {
      if (!o(t2) || 0 === t2.getClientRects().length)
        return false;
      const e2 = "visible" === getComputedStyle(t2).getPropertyValue("visibility"), i2 = t2.closest("details:not([open])");
      if (!i2)
        return e2;
      if (i2 !== t2) {
        const e3 = t2.closest("summary");
        if (e3 && e3.parentNode !== i2)
          return false;
        if (null === e3)
          return false;
      }
      return e2;
    }, l = (t2) => !t2 || t2.nodeType !== Node.ELEMENT_NODE || !!t2.classList.contains("disabled") || (void 0 !== t2.disabled ? t2.disabled : t2.hasAttribute("disabled") && "false" !== t2.getAttribute("disabled")), c = (t2) => {
      if (!document.documentElement.attachShadow)
        return null;
      if ("function" == typeof t2.getRootNode) {
        const e2 = t2.getRootNode();
        return e2 instanceof ShadowRoot ? e2 : null;
      }
      return t2 instanceof ShadowRoot ? t2 : t2.parentNode ? c(t2.parentNode) : null;
    }, h = () => {
    }, d = (t2) => {
      t2.offsetHeight;
    }, u = () => window.jQuery && !document.body.hasAttribute("data-bs-no-jquery") ? window.jQuery : null, f = [], p2 = () => "rtl" === document.documentElement.dir, m3 = (t2) => {
      var e2;
      e2 = () => {
        const e3 = u();
        if (e3) {
          const i2 = t2.NAME, n2 = e3.fn[i2];
          e3.fn[i2] = t2.jQueryInterface, e3.fn[i2].Constructor = t2, e3.fn[i2].noConflict = () => (e3.fn[i2] = n2, t2.jQueryInterface);
        }
      }, "loading" === document.readyState ? (f.length || document.addEventListener("DOMContentLoaded", () => {
        for (const t3 of f)
          t3();
      }), f.push(e2)) : e2();
    }, g = (t2, e2 = [], i2 = t2) => "function" == typeof t2 ? t2(...e2) : i2, _ = (t2, e2, n2 = true) => {
      if (!n2)
        return void g(t2);
      const o2 = ((t3) => {
        if (!t3)
          return 0;
        let { transitionDuration: e3, transitionDelay: i2 } = window.getComputedStyle(t3);
        const n3 = Number.parseFloat(e3), s2 = Number.parseFloat(i2);
        return n3 || s2 ? (e3 = e3.split(",")[0], i2 = i2.split(",")[0], 1e3 * (Number.parseFloat(e3) + Number.parseFloat(i2))) : 0;
      })(e2) + 5;
      let r2 = false;
      const a2 = ({ target: n3 }) => {
        n3 === e2 && (r2 = true, e2.removeEventListener(i, a2), g(t2));
      };
      e2.addEventListener(i, a2), setTimeout(() => {
        r2 || s(e2);
      }, o2);
    }, b = (t2, e2, i2, n2) => {
      const s2 = t2.length;
      let o2 = t2.indexOf(e2);
      return -1 === o2 ? !i2 && n2 ? t2[s2 - 1] : t2[0] : (o2 += i2 ? 1 : -1, n2 && (o2 = (o2 + s2) % s2), t2[Math.max(0, Math.min(o2, s2 - 1))]);
    }, v = /[^.]*(?=\..*)\.|.*/, y = /\..*/, w = /::\d+$/, A = {};
    let E = 1;
    const T = { mouseenter: "mouseover", mouseleave: "mouseout" }, C = /* @__PURE__ */ new Set(["click", "dblclick", "mouseup", "mousedown", "contextmenu", "mousewheel", "DOMMouseScroll", "mouseover", "mouseout", "mousemove", "selectstart", "selectend", "keydown", "keypress", "keyup", "orientationchange", "touchstart", "touchmove", "touchend", "touchcancel", "pointerdown", "pointermove", "pointerup", "pointerleave", "pointercancel", "gesturestart", "gesturechange", "gestureend", "focus", "blur", "change", "reset", "select", "submit", "focusin", "focusout", "load", "unload", "beforeunload", "resize", "move", "DOMContentLoaded", "readystatechange", "error", "abort", "scroll"]);
    function O(t2, e2) {
      return e2 && `${e2}::${E++}` || t2.uidEvent || E++;
    }
    function x(t2) {
      const e2 = O(t2);
      return t2.uidEvent = e2, A[e2] = A[e2] || {}, A[e2];
    }
    function k(t2, e2, i2 = null) {
      return Object.values(t2).find((t3) => t3.callable === e2 && t3.delegationSelector === i2);
    }
    function L(t2, e2, i2) {
      const n2 = "string" == typeof e2, s2 = n2 ? i2 : e2 || i2;
      let o2 = I(t2);
      return C.has(o2) || (o2 = t2), [n2, s2, o2];
    }
    function S(t2, e2, i2, n2, s2) {
      if ("string" != typeof e2 || !t2)
        return;
      let [o2, r2, a2] = L(e2, i2, n2);
      if (e2 in T) {
        const t3 = (t4) => function(e3) {
          if (!e3.relatedTarget || e3.relatedTarget !== e3.delegateTarget && !e3.delegateTarget.contains(e3.relatedTarget))
            return t4.call(this, e3);
        };
        r2 = t3(r2);
      }
      const l2 = x(t2), c2 = l2[a2] || (l2[a2] = {}), h2 = k(c2, r2, o2 ? i2 : null);
      if (h2)
        return void (h2.oneOff = h2.oneOff && s2);
      const d2 = O(r2, e2.replace(v, "")), u2 = o2 ? function(t3, e3, i3) {
        return function n3(s3) {
          const o3 = t3.querySelectorAll(e3);
          for (let { target: r3 } = s3; r3 && r3 !== this; r3 = r3.parentNode)
            for (const a3 of o3)
              if (a3 === r3)
                return P(s3, { delegateTarget: r3 }), n3.oneOff && N.off(t3, s3.type, e3, i3), i3.apply(r3, [s3]);
        };
      }(t2, i2, r2) : function(t3, e3) {
        return function i3(n3) {
          return P(n3, { delegateTarget: t3 }), i3.oneOff && N.off(t3, n3.type, e3), e3.apply(t3, [n3]);
        };
      }(t2, r2);
      u2.delegationSelector = o2 ? i2 : null, u2.callable = r2, u2.oneOff = s2, u2.uidEvent = d2, c2[d2] = u2, t2.addEventListener(a2, u2, o2);
    }
    function D(t2, e2, i2, n2, s2) {
      const o2 = k(e2[i2], n2, s2);
      o2 && (t2.removeEventListener(i2, o2, Boolean(s2)), delete e2[i2][o2.uidEvent]);
    }
    function $(t2, e2, i2, n2) {
      const s2 = e2[i2] || {};
      for (const [o2, r2] of Object.entries(s2))
        o2.includes(n2) && D(t2, e2, i2, r2.callable, r2.delegationSelector);
    }
    function I(t2) {
      return t2 = t2.replace(y, ""), T[t2] || t2;
    }
    const N = { on(t2, e2, i2, n2) {
      S(t2, e2, i2, n2, false);
    }, one(t2, e2, i2, n2) {
      S(t2, e2, i2, n2, true);
    }, off(t2, e2, i2, n2) {
      if ("string" != typeof e2 || !t2)
        return;
      const [s2, o2, r2] = L(e2, i2, n2), a2 = r2 !== e2, l2 = x(t2), c2 = l2[r2] || {}, h2 = e2.startsWith(".");
      if (void 0 === o2) {
        if (h2)
          for (const i3 of Object.keys(l2))
            $(t2, l2, i3, e2.slice(1));
        for (const [i3, n3] of Object.entries(c2)) {
          const s3 = i3.replace(w, "");
          a2 && !e2.includes(s3) || D(t2, l2, r2, n3.callable, n3.delegationSelector);
        }
      } else {
        if (!Object.keys(c2).length)
          return;
        D(t2, l2, r2, o2, s2 ? i2 : null);
      }
    }, trigger(t2, e2, i2) {
      if ("string" != typeof e2 || !t2)
        return null;
      const n2 = u();
      let s2 = null, o2 = true, r2 = true, a2 = false;
      e2 !== I(e2) && n2 && (s2 = n2.Event(e2, i2), n2(t2).trigger(s2), o2 = !s2.isPropagationStopped(), r2 = !s2.isImmediatePropagationStopped(), a2 = s2.isDefaultPrevented());
      const l2 = P(new Event(e2, { bubbles: o2, cancelable: true }), i2);
      return a2 && l2.preventDefault(), r2 && t2.dispatchEvent(l2), l2.defaultPrevented && s2 && s2.preventDefault(), l2;
    } };
    function P(t2, e2 = {}) {
      for (const [i2, n2] of Object.entries(e2))
        try {
          t2[i2] = n2;
        } catch (e3) {
          Object.defineProperty(t2, i2, { configurable: true, get: () => n2 });
        }
      return t2;
    }
    function j(t2) {
      if ("true" === t2)
        return true;
      if ("false" === t2)
        return false;
      if (t2 === Number(t2).toString())
        return Number(t2);
      if ("" === t2 || "null" === t2)
        return null;
      if ("string" != typeof t2)
        return t2;
      try {
        return JSON.parse(decodeURIComponent(t2));
      } catch (e2) {
        return t2;
      }
    }
    function M(t2) {
      return t2.replace(/[A-Z]/g, (t3) => `-${t3.toLowerCase()}`);
    }
    const F = { setDataAttribute(t2, e2, i2) {
      t2.setAttribute(`data-bs-${M(e2)}`, i2);
    }, removeDataAttribute(t2, e2) {
      t2.removeAttribute(`data-bs-${M(e2)}`);
    }, getDataAttributes(t2) {
      if (!t2)
        return {};
      const e2 = {}, i2 = Object.keys(t2.dataset).filter((t3) => t3.startsWith("bs") && !t3.startsWith("bsConfig"));
      for (const n2 of i2) {
        let i3 = n2.replace(/^bs/, "");
        i3 = i3.charAt(0).toLowerCase() + i3.slice(1, i3.length), e2[i3] = j(t2.dataset[n2]);
      }
      return e2;
    }, getDataAttribute: (t2, e2) => j(t2.getAttribute(`data-bs-${M(e2)}`)) };
    class H {
      static get Default() {
        return {};
      }
      static get DefaultType() {
        return {};
      }
      static get NAME() {
        throw new Error('You have to implement the static method "NAME", for each component!');
      }
      _getConfig(t2) {
        return t2 = this._mergeConfigObj(t2), t2 = this._configAfterMerge(t2), this._typeCheckConfig(t2), t2;
      }
      _configAfterMerge(t2) {
        return t2;
      }
      _mergeConfigObj(t2, e2) {
        const i2 = o(e2) ? F.getDataAttribute(e2, "config") : {};
        return { ...this.constructor.Default, ..."object" == typeof i2 ? i2 : {}, ...o(e2) ? F.getDataAttributes(e2) : {}, ..."object" == typeof t2 ? t2 : {} };
      }
      _typeCheckConfig(t2, e2 = this.constructor.DefaultType) {
        for (const [n2, s2] of Object.entries(e2)) {
          const e3 = t2[n2], r2 = o(e3) ? "element" : null == (i2 = e3) ? `${i2}` : Object.prototype.toString.call(i2).match(/\s([a-z]+)/i)[1].toLowerCase();
          if (!new RegExp(s2).test(r2))
            throw new TypeError(`${this.constructor.NAME.toUpperCase()}: Option "${n2}" provided type "${r2}" but expected type "${s2}".`);
        }
        var i2;
      }
    }
    class W extends H {
      constructor(t2, i2) {
        super(), (t2 = r(t2)) && (this._element = t2, this._config = this._getConfig(i2), e.set(this._element, this.constructor.DATA_KEY, this));
      }
      dispose() {
        e.remove(this._element, this.constructor.DATA_KEY), N.off(this._element, this.constructor.EVENT_KEY);
        for (const t2 of Object.getOwnPropertyNames(this))
          this[t2] = null;
      }
      _queueCallback(t2, e2, i2 = true) {
        _(t2, e2, i2);
      }
      _getConfig(t2) {
        return t2 = this._mergeConfigObj(t2, this._element), t2 = this._configAfterMerge(t2), this._typeCheckConfig(t2), t2;
      }
      static getInstance(t2) {
        return e.get(r(t2), this.DATA_KEY);
      }
      static getOrCreateInstance(t2, e2 = {}) {
        return this.getInstance(t2) || new this(t2, "object" == typeof e2 ? e2 : null);
      }
      static get VERSION() {
        return "5.3.3";
      }
      static get DATA_KEY() {
        return `bs.${this.NAME}`;
      }
      static get EVENT_KEY() {
        return `.${this.DATA_KEY}`;
      }
      static eventName(t2) {
        return `${t2}${this.EVENT_KEY}`;
      }
    }
    const B = (t2) => {
      let e2 = t2.getAttribute("data-bs-target");
      if (!e2 || "#" === e2) {
        let i2 = t2.getAttribute("href");
        if (!i2 || !i2.includes("#") && !i2.startsWith("."))
          return null;
        i2.includes("#") && !i2.startsWith("#") && (i2 = `#${i2.split("#")[1]}`), e2 = i2 && "#" !== i2 ? i2.trim() : null;
      }
      return e2 ? e2.split(",").map((t3) => n(t3)).join(",") : null;
    }, z = { find: (t2, e2 = document.documentElement) => [].concat(...Element.prototype.querySelectorAll.call(e2, t2)), findOne: (t2, e2 = document.documentElement) => Element.prototype.querySelector.call(e2, t2), children: (t2, e2) => [].concat(...t2.children).filter((t3) => t3.matches(e2)), parents(t2, e2) {
      const i2 = [];
      let n2 = t2.parentNode.closest(e2);
      for (; n2; )
        i2.push(n2), n2 = n2.parentNode.closest(e2);
      return i2;
    }, prev(t2, e2) {
      let i2 = t2.previousElementSibling;
      for (; i2; ) {
        if (i2.matches(e2))
          return [i2];
        i2 = i2.previousElementSibling;
      }
      return [];
    }, next(t2, e2) {
      let i2 = t2.nextElementSibling;
      for (; i2; ) {
        if (i2.matches(e2))
          return [i2];
        i2 = i2.nextElementSibling;
      }
      return [];
    }, focusableChildren(t2) {
      const e2 = ["a", "button", "input", "textarea", "select", "details", "[tabindex]", '[contenteditable="true"]'].map((t3) => `${t3}:not([tabindex^="-"])`).join(",");
      return this.find(e2, t2).filter((t3) => !l(t3) && a(t3));
    }, getSelectorFromElement(t2) {
      const e2 = B(t2);
      return e2 && z.findOne(e2) ? e2 : null;
    }, getElementFromSelector(t2) {
      const e2 = B(t2);
      return e2 ? z.findOne(e2) : null;
    }, getMultipleElementsFromSelector(t2) {
      const e2 = B(t2);
      return e2 ? z.find(e2) : [];
    } }, R = (t2, e2 = "hide") => {
      const i2 = `click.dismiss${t2.EVENT_KEY}`, n2 = t2.NAME;
      N.on(document, i2, `[data-bs-dismiss="${n2}"]`, function(i3) {
        if (["A", "AREA"].includes(this.tagName) && i3.preventDefault(), l(this))
          return;
        const s2 = z.getElementFromSelector(this) || this.closest(`.${n2}`);
        t2.getOrCreateInstance(s2)[e2]();
      });
    }, q = ".bs.alert", V = `close${q}`, K = `closed${q}`;
    class Q extends W {
      static get NAME() {
        return "alert";
      }
      close() {
        if (N.trigger(this._element, V).defaultPrevented)
          return;
        this._element.classList.remove("show");
        const t2 = this._element.classList.contains("fade");
        this._queueCallback(() => this._destroyElement(), this._element, t2);
      }
      _destroyElement() {
        this._element.remove(), N.trigger(this._element, K), this.dispose();
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = Q.getOrCreateInstance(this);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2] || t2.startsWith("_") || "constructor" === t2)
              throw new TypeError(`No method named "${t2}"`);
            e2[t2](this);
          }
        });
      }
    }
    R(Q, "close"), m3(Q);
    const X = '[data-bs-toggle="button"]';
    class Y extends W {
      static get NAME() {
        return "button";
      }
      toggle() {
        this._element.setAttribute("aria-pressed", this._element.classList.toggle("active"));
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = Y.getOrCreateInstance(this);
          "toggle" === t2 && e2[t2]();
        });
      }
    }
    N.on(document, "click.bs.button.data-api", X, (t2) => {
      t2.preventDefault();
      const e2 = t2.target.closest(X);
      Y.getOrCreateInstance(e2).toggle();
    }), m3(Y);
    const U = ".bs.swipe", G = `touchstart${U}`, J = `touchmove${U}`, Z = `touchend${U}`, tt = `pointerdown${U}`, et = `pointerup${U}`, it = { endCallback: null, leftCallback: null, rightCallback: null }, nt = { endCallback: "(function|null)", leftCallback: "(function|null)", rightCallback: "(function|null)" };
    class st extends H {
      constructor(t2, e2) {
        super(), this._element = t2, t2 && st.isSupported() && (this._config = this._getConfig(e2), this._deltaX = 0, this._supportPointerEvents = Boolean(window.PointerEvent), this._initEvents());
      }
      static get Default() {
        return it;
      }
      static get DefaultType() {
        return nt;
      }
      static get NAME() {
        return "swipe";
      }
      dispose() {
        N.off(this._element, U);
      }
      _start(t2) {
        this._supportPointerEvents ? this._eventIsPointerPenTouch(t2) && (this._deltaX = t2.clientX) : this._deltaX = t2.touches[0].clientX;
      }
      _end(t2) {
        this._eventIsPointerPenTouch(t2) && (this._deltaX = t2.clientX - this._deltaX), this._handleSwipe(), g(this._config.endCallback);
      }
      _move(t2) {
        this._deltaX = t2.touches && t2.touches.length > 1 ? 0 : t2.touches[0].clientX - this._deltaX;
      }
      _handleSwipe() {
        const t2 = Math.abs(this._deltaX);
        if (t2 <= 40)
          return;
        const e2 = t2 / this._deltaX;
        this._deltaX = 0, e2 && g(e2 > 0 ? this._config.rightCallback : this._config.leftCallback);
      }
      _initEvents() {
        this._supportPointerEvents ? (N.on(this._element, tt, (t2) => this._start(t2)), N.on(this._element, et, (t2) => this._end(t2)), this._element.classList.add("pointer-event")) : (N.on(this._element, G, (t2) => this._start(t2)), N.on(this._element, J, (t2) => this._move(t2)), N.on(this._element, Z, (t2) => this._end(t2)));
      }
      _eventIsPointerPenTouch(t2) {
        return this._supportPointerEvents && ("pen" === t2.pointerType || "touch" === t2.pointerType);
      }
      static isSupported() {
        return "ontouchstart" in document.documentElement || navigator.maxTouchPoints > 0;
      }
    }
    const ot = ".bs.carousel", rt = ".data-api", at = "next", lt = "prev", ct = "left", ht = "right", dt = `slide${ot}`, ut = `slid${ot}`, ft = `keydown${ot}`, pt = `mouseenter${ot}`, mt = `mouseleave${ot}`, gt = `dragstart${ot}`, _t = `load${ot}${rt}`, bt = `click${ot}${rt}`, vt = "carousel", yt = "active", wt = ".active", At = ".carousel-item", Et = wt + At, Tt = { ArrowLeft: ht, ArrowRight: ct }, Ct = { interval: 5e3, keyboard: true, pause: "hover", ride: false, touch: true, wrap: true }, Ot = { interval: "(number|boolean)", keyboard: "boolean", pause: "(string|boolean)", ride: "(boolean|string)", touch: "boolean", wrap: "boolean" };
    class xt extends W {
      constructor(t2, e2) {
        super(t2, e2), this._interval = null, this._activeElement = null, this._isSliding = false, this.touchTimeout = null, this._swipeHelper = null, this._indicatorsElement = z.findOne(".carousel-indicators", this._element), this._addEventListeners(), this._config.ride === vt && this.cycle();
      }
      static get Default() {
        return Ct;
      }
      static get DefaultType() {
        return Ot;
      }
      static get NAME() {
        return "carousel";
      }
      next() {
        this._slide(at);
      }
      nextWhenVisible() {
        !document.hidden && a(this._element) && this.next();
      }
      prev() {
        this._slide(lt);
      }
      pause() {
        this._isSliding && s(this._element), this._clearInterval();
      }
      cycle() {
        this._clearInterval(), this._updateInterval(), this._interval = setInterval(() => this.nextWhenVisible(), this._config.interval);
      }
      _maybeEnableCycle() {
        this._config.ride && (this._isSliding ? N.one(this._element, ut, () => this.cycle()) : this.cycle());
      }
      to(t2) {
        const e2 = this._getItems();
        if (t2 > e2.length - 1 || t2 < 0)
          return;
        if (this._isSliding)
          return void N.one(this._element, ut, () => this.to(t2));
        const i2 = this._getItemIndex(this._getActive());
        if (i2 === t2)
          return;
        const n2 = t2 > i2 ? at : lt;
        this._slide(n2, e2[t2]);
      }
      dispose() {
        this._swipeHelper && this._swipeHelper.dispose(), super.dispose();
      }
      _configAfterMerge(t2) {
        return t2.defaultInterval = t2.interval, t2;
      }
      _addEventListeners() {
        this._config.keyboard && N.on(this._element, ft, (t2) => this._keydown(t2)), "hover" === this._config.pause && (N.on(this._element, pt, () => this.pause()), N.on(this._element, mt, () => this._maybeEnableCycle())), this._config.touch && st.isSupported() && this._addTouchEventListeners();
      }
      _addTouchEventListeners() {
        for (const t3 of z.find(".carousel-item img", this._element))
          N.on(t3, gt, (t4) => t4.preventDefault());
        const t2 = { leftCallback: () => this._slide(this._directionToOrder(ct)), rightCallback: () => this._slide(this._directionToOrder(ht)), endCallback: () => {
          "hover" === this._config.pause && (this.pause(), this.touchTimeout && clearTimeout(this.touchTimeout), this.touchTimeout = setTimeout(() => this._maybeEnableCycle(), 500 + this._config.interval));
        } };
        this._swipeHelper = new st(this._element, t2);
      }
      _keydown(t2) {
        if (/input|textarea/i.test(t2.target.tagName))
          return;
        const e2 = Tt[t2.key];
        e2 && (t2.preventDefault(), this._slide(this._directionToOrder(e2)));
      }
      _getItemIndex(t2) {
        return this._getItems().indexOf(t2);
      }
      _setActiveIndicatorElement(t2) {
        if (!this._indicatorsElement)
          return;
        const e2 = z.findOne(wt, this._indicatorsElement);
        e2.classList.remove(yt), e2.removeAttribute("aria-current");
        const i2 = z.findOne(`[data-bs-slide-to="${t2}"]`, this._indicatorsElement);
        i2 && (i2.classList.add(yt), i2.setAttribute("aria-current", "true"));
      }
      _updateInterval() {
        const t2 = this._activeElement || this._getActive();
        if (!t2)
          return;
        const e2 = Number.parseInt(t2.getAttribute("data-bs-interval"), 10);
        this._config.interval = e2 || this._config.defaultInterval;
      }
      _slide(t2, e2 = null) {
        if (this._isSliding)
          return;
        const i2 = this._getActive(), n2 = t2 === at, s2 = e2 || b(this._getItems(), i2, n2, this._config.wrap);
        if (s2 === i2)
          return;
        const o2 = this._getItemIndex(s2), r2 = (e3) => N.trigger(this._element, e3, { relatedTarget: s2, direction: this._orderToDirection(t2), from: this._getItemIndex(i2), to: o2 });
        if (r2(dt).defaultPrevented)
          return;
        if (!i2 || !s2)
          return;
        const a2 = Boolean(this._interval);
        this.pause(), this._isSliding = true, this._setActiveIndicatorElement(o2), this._activeElement = s2;
        const l2 = n2 ? "carousel-item-start" : "carousel-item-end", c2 = n2 ? "carousel-item-next" : "carousel-item-prev";
        s2.classList.add(c2), d(s2), i2.classList.add(l2), s2.classList.add(l2), this._queueCallback(() => {
          s2.classList.remove(l2, c2), s2.classList.add(yt), i2.classList.remove(yt, c2, l2), this._isSliding = false, r2(ut);
        }, i2, this._isAnimated()), a2 && this.cycle();
      }
      _isAnimated() {
        return this._element.classList.contains("slide");
      }
      _getActive() {
        return z.findOne(Et, this._element);
      }
      _getItems() {
        return z.find(At, this._element);
      }
      _clearInterval() {
        this._interval && (clearInterval(this._interval), this._interval = null);
      }
      _directionToOrder(t2) {
        return p2() ? t2 === ct ? lt : at : t2 === ct ? at : lt;
      }
      _orderToDirection(t2) {
        return p2() ? t2 === lt ? ct : ht : t2 === lt ? ht : ct;
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = xt.getOrCreateInstance(this, t2);
          if ("number" != typeof t2) {
            if ("string" == typeof t2) {
              if (void 0 === e2[t2] || t2.startsWith("_") || "constructor" === t2)
                throw new TypeError(`No method named "${t2}"`);
              e2[t2]();
            }
          } else
            e2.to(t2);
        });
      }
    }
    N.on(document, bt, "[data-bs-slide], [data-bs-slide-to]", function(t2) {
      const e2 = z.getElementFromSelector(this);
      if (!e2 || !e2.classList.contains(vt))
        return;
      t2.preventDefault();
      const i2 = xt.getOrCreateInstance(e2), n2 = this.getAttribute("data-bs-slide-to");
      return n2 ? (i2.to(n2), void i2._maybeEnableCycle()) : "next" === F.getDataAttribute(this, "slide") ? (i2.next(), void i2._maybeEnableCycle()) : (i2.prev(), void i2._maybeEnableCycle());
    }), N.on(window, _t, () => {
      const t2 = z.find('[data-bs-ride="carousel"]');
      for (const e2 of t2)
        xt.getOrCreateInstance(e2);
    }), m3(xt);
    const kt = ".bs.collapse", Lt = `show${kt}`, St = `shown${kt}`, Dt = `hide${kt}`, $t = `hidden${kt}`, It = `click${kt}.data-api`, Nt = "show", Pt = "collapse", jt = "collapsing", Mt = `:scope .${Pt} .${Pt}`, Ft = '[data-bs-toggle="collapse"]', Ht = { parent: null, toggle: true }, Wt = { parent: "(null|element)", toggle: "boolean" };
    class Bt extends W {
      constructor(t2, e2) {
        super(t2, e2), this._isTransitioning = false, this._triggerArray = [];
        const i2 = z.find(Ft);
        for (const t3 of i2) {
          const e3 = z.getSelectorFromElement(t3), i3 = z.find(e3).filter((t4) => t4 === this._element);
          null !== e3 && i3.length && this._triggerArray.push(t3);
        }
        this._initializeChildren(), this._config.parent || this._addAriaAndCollapsedClass(this._triggerArray, this._isShown()), this._config.toggle && this.toggle();
      }
      static get Default() {
        return Ht;
      }
      static get DefaultType() {
        return Wt;
      }
      static get NAME() {
        return "collapse";
      }
      toggle() {
        this._isShown() ? this.hide() : this.show();
      }
      show() {
        if (this._isTransitioning || this._isShown())
          return;
        let t2 = [];
        if (this._config.parent && (t2 = this._getFirstLevelChildren(".collapse.show, .collapse.collapsing").filter((t3) => t3 !== this._element).map((t3) => Bt.getOrCreateInstance(t3, { toggle: false }))), t2.length && t2[0]._isTransitioning)
          return;
        if (N.trigger(this._element, Lt).defaultPrevented)
          return;
        for (const e3 of t2)
          e3.hide();
        const e2 = this._getDimension();
        this._element.classList.remove(Pt), this._element.classList.add(jt), this._element.style[e2] = 0, this._addAriaAndCollapsedClass(this._triggerArray, true), this._isTransitioning = true;
        const i2 = `scroll${e2[0].toUpperCase() + e2.slice(1)}`;
        this._queueCallback(() => {
          this._isTransitioning = false, this._element.classList.remove(jt), this._element.classList.add(Pt, Nt), this._element.style[e2] = "", N.trigger(this._element, St);
        }, this._element, true), this._element.style[e2] = `${this._element[i2]}px`;
      }
      hide() {
        if (this._isTransitioning || !this._isShown())
          return;
        if (N.trigger(this._element, Dt).defaultPrevented)
          return;
        const t2 = this._getDimension();
        this._element.style[t2] = `${this._element.getBoundingClientRect()[t2]}px`, d(this._element), this._element.classList.add(jt), this._element.classList.remove(Pt, Nt);
        for (const t3 of this._triggerArray) {
          const e2 = z.getElementFromSelector(t3);
          e2 && !this._isShown(e2) && this._addAriaAndCollapsedClass([t3], false);
        }
        this._isTransitioning = true, this._element.style[t2] = "", this._queueCallback(() => {
          this._isTransitioning = false, this._element.classList.remove(jt), this._element.classList.add(Pt), N.trigger(this._element, $t);
        }, this._element, true);
      }
      _isShown(t2 = this._element) {
        return t2.classList.contains(Nt);
      }
      _configAfterMerge(t2) {
        return t2.toggle = Boolean(t2.toggle), t2.parent = r(t2.parent), t2;
      }
      _getDimension() {
        return this._element.classList.contains("collapse-horizontal") ? "width" : "height";
      }
      _initializeChildren() {
        if (!this._config.parent)
          return;
        const t2 = this._getFirstLevelChildren(Ft);
        for (const e2 of t2) {
          const t3 = z.getElementFromSelector(e2);
          t3 && this._addAriaAndCollapsedClass([e2], this._isShown(t3));
        }
      }
      _getFirstLevelChildren(t2) {
        const e2 = z.find(Mt, this._config.parent);
        return z.find(t2, this._config.parent).filter((t3) => !e2.includes(t3));
      }
      _addAriaAndCollapsedClass(t2, e2) {
        if (t2.length)
          for (const i2 of t2)
            i2.classList.toggle("collapsed", !e2), i2.setAttribute("aria-expanded", e2);
      }
      static jQueryInterface(t2) {
        const e2 = {};
        return "string" == typeof t2 && /show|hide/.test(t2) && (e2.toggle = false), this.each(function() {
          const i2 = Bt.getOrCreateInstance(this, e2);
          if ("string" == typeof t2) {
            if (void 0 === i2[t2])
              throw new TypeError(`No method named "${t2}"`);
            i2[t2]();
          }
        });
      }
    }
    N.on(document, It, Ft, function(t2) {
      ("A" === t2.target.tagName || t2.delegateTarget && "A" === t2.delegateTarget.tagName) && t2.preventDefault();
      for (const t3 of z.getMultipleElementsFromSelector(this))
        Bt.getOrCreateInstance(t3, { toggle: false }).toggle();
    }), m3(Bt);
    var zt = "top", Rt = "bottom", qt = "right", Vt = "left", Kt = "auto", Qt = [zt, Rt, qt, Vt], Xt = "start", Yt = "end", Ut = "clippingParents", Gt = "viewport", Jt = "popper", Zt = "reference", te = Qt.reduce(function(t2, e2) {
      return t2.concat([e2 + "-" + Xt, e2 + "-" + Yt]);
    }, []), ee = [].concat(Qt, [Kt]).reduce(function(t2, e2) {
      return t2.concat([e2, e2 + "-" + Xt, e2 + "-" + Yt]);
    }, []), ie = "beforeRead", ne = "read", se = "afterRead", oe = "beforeMain", re = "main", ae = "afterMain", le = "beforeWrite", ce = "write", he = "afterWrite", de = [ie, ne, se, oe, re, ae, le, ce, he];
    function ue(t2) {
      return t2 ? (t2.nodeName || "").toLowerCase() : null;
    }
    function fe(t2) {
      if (null == t2)
        return window;
      if ("[object Window]" !== t2.toString()) {
        var e2 = t2.ownerDocument;
        return e2 && e2.defaultView || window;
      }
      return t2;
    }
    function pe(t2) {
      return t2 instanceof fe(t2).Element || t2 instanceof Element;
    }
    function me(t2) {
      return t2 instanceof fe(t2).HTMLElement || t2 instanceof HTMLElement;
    }
    function ge(t2) {
      return "undefined" != typeof ShadowRoot && (t2 instanceof fe(t2).ShadowRoot || t2 instanceof ShadowRoot);
    }
    const _e = { name: "applyStyles", enabled: true, phase: "write", fn: function(t2) {
      var e2 = t2.state;
      Object.keys(e2.elements).forEach(function(t3) {
        var i2 = e2.styles[t3] || {}, n2 = e2.attributes[t3] || {}, s2 = e2.elements[t3];
        me(s2) && ue(s2) && (Object.assign(s2.style, i2), Object.keys(n2).forEach(function(t4) {
          var e3 = n2[t4];
          false === e3 ? s2.removeAttribute(t4) : s2.setAttribute(t4, true === e3 ? "" : e3);
        }));
      });
    }, effect: function(t2) {
      var e2 = t2.state, i2 = { popper: { position: e2.options.strategy, left: "0", top: "0", margin: "0" }, arrow: { position: "absolute" }, reference: {} };
      return Object.assign(e2.elements.popper.style, i2.popper), e2.styles = i2, e2.elements.arrow && Object.assign(e2.elements.arrow.style, i2.arrow), function() {
        Object.keys(e2.elements).forEach(function(t3) {
          var n2 = e2.elements[t3], s2 = e2.attributes[t3] || {}, o2 = Object.keys(e2.styles.hasOwnProperty(t3) ? e2.styles[t3] : i2[t3]).reduce(function(t4, e3) {
            return t4[e3] = "", t4;
          }, {});
          me(n2) && ue(n2) && (Object.assign(n2.style, o2), Object.keys(s2).forEach(function(t4) {
            n2.removeAttribute(t4);
          }));
        });
      };
    }, requires: ["computeStyles"] };
    function be(t2) {
      return t2.split("-")[0];
    }
    var ve = Math.max, ye = Math.min, we = Math.round;
    function Ae() {
      var t2 = navigator.userAgentData;
      return null != t2 && t2.brands && Array.isArray(t2.brands) ? t2.brands.map(function(t3) {
        return t3.brand + "/" + t3.version;
      }).join(" ") : navigator.userAgent;
    }
    function Ee() {
      return !/^((?!chrome|android).)*safari/i.test(Ae());
    }
    function Te(t2, e2, i2) {
      void 0 === e2 && (e2 = false), void 0 === i2 && (i2 = false);
      var n2 = t2.getBoundingClientRect(), s2 = 1, o2 = 1;
      e2 && me(t2) && (s2 = t2.offsetWidth > 0 && we(n2.width) / t2.offsetWidth || 1, o2 = t2.offsetHeight > 0 && we(n2.height) / t2.offsetHeight || 1);
      var r2 = (pe(t2) ? fe(t2) : window).visualViewport, a2 = !Ee() && i2, l2 = (n2.left + (a2 && r2 ? r2.offsetLeft : 0)) / s2, c2 = (n2.top + (a2 && r2 ? r2.offsetTop : 0)) / o2, h2 = n2.width / s2, d2 = n2.height / o2;
      return { width: h2, height: d2, top: c2, right: l2 + h2, bottom: c2 + d2, left: l2, x: l2, y: c2 };
    }
    function Ce(t2) {
      var e2 = Te(t2), i2 = t2.offsetWidth, n2 = t2.offsetHeight;
      return Math.abs(e2.width - i2) <= 1 && (i2 = e2.width), Math.abs(e2.height - n2) <= 1 && (n2 = e2.height), { x: t2.offsetLeft, y: t2.offsetTop, width: i2, height: n2 };
    }
    function Oe(t2, e2) {
      var i2 = e2.getRootNode && e2.getRootNode();
      if (t2.contains(e2))
        return true;
      if (i2 && ge(i2)) {
        var n2 = e2;
        do {
          if (n2 && t2.isSameNode(n2))
            return true;
          n2 = n2.parentNode || n2.host;
        } while (n2);
      }
      return false;
    }
    function xe(t2) {
      return fe(t2).getComputedStyle(t2);
    }
    function ke(t2) {
      return ["table", "td", "th"].indexOf(ue(t2)) >= 0;
    }
    function Le(t2) {
      return ((pe(t2) ? t2.ownerDocument : t2.document) || window.document).documentElement;
    }
    function Se(t2) {
      return "html" === ue(t2) ? t2 : t2.assignedSlot || t2.parentNode || (ge(t2) ? t2.host : null) || Le(t2);
    }
    function De(t2) {
      return me(t2) && "fixed" !== xe(t2).position ? t2.offsetParent : null;
    }
    function $e(t2) {
      for (var e2 = fe(t2), i2 = De(t2); i2 && ke(i2) && "static" === xe(i2).position; )
        i2 = De(i2);
      return i2 && ("html" === ue(i2) || "body" === ue(i2) && "static" === xe(i2).position) ? e2 : i2 || function(t3) {
        var e3 = /firefox/i.test(Ae());
        if (/Trident/i.test(Ae()) && me(t3) && "fixed" === xe(t3).position)
          return null;
        var i3 = Se(t3);
        for (ge(i3) && (i3 = i3.host); me(i3) && ["html", "body"].indexOf(ue(i3)) < 0; ) {
          var n2 = xe(i3);
          if ("none" !== n2.transform || "none" !== n2.perspective || "paint" === n2.contain || -1 !== ["transform", "perspective"].indexOf(n2.willChange) || e3 && "filter" === n2.willChange || e3 && n2.filter && "none" !== n2.filter)
            return i3;
          i3 = i3.parentNode;
        }
        return null;
      }(t2) || e2;
    }
    function Ie(t2) {
      return ["top", "bottom"].indexOf(t2) >= 0 ? "x" : "y";
    }
    function Ne(t2, e2, i2) {
      return ve(t2, ye(e2, i2));
    }
    function Pe(t2) {
      return Object.assign({}, { top: 0, right: 0, bottom: 0, left: 0 }, t2);
    }
    function je(t2, e2) {
      return e2.reduce(function(e3, i2) {
        return e3[i2] = t2, e3;
      }, {});
    }
    const Me = { name: "arrow", enabled: true, phase: "main", fn: function(t2) {
      var e2, i2 = t2.state, n2 = t2.name, s2 = t2.options, o2 = i2.elements.arrow, r2 = i2.modifiersData.popperOffsets, a2 = be(i2.placement), l2 = Ie(a2), c2 = [Vt, qt].indexOf(a2) >= 0 ? "height" : "width";
      if (o2 && r2) {
        var h2 = function(t3, e3) {
          return Pe("number" != typeof (t3 = "function" == typeof t3 ? t3(Object.assign({}, e3.rects, { placement: e3.placement })) : t3) ? t3 : je(t3, Qt));
        }(s2.padding, i2), d2 = Ce(o2), u2 = "y" === l2 ? zt : Vt, f2 = "y" === l2 ? Rt : qt, p3 = i2.rects.reference[c2] + i2.rects.reference[l2] - r2[l2] - i2.rects.popper[c2], m4 = r2[l2] - i2.rects.reference[l2], g2 = $e(o2), _2 = g2 ? "y" === l2 ? g2.clientHeight || 0 : g2.clientWidth || 0 : 0, b2 = p3 / 2 - m4 / 2, v2 = h2[u2], y2 = _2 - d2[c2] - h2[f2], w2 = _2 / 2 - d2[c2] / 2 + b2, A2 = Ne(v2, w2, y2), E2 = l2;
        i2.modifiersData[n2] = ((e2 = {})[E2] = A2, e2.centerOffset = A2 - w2, e2);
      }
    }, effect: function(t2) {
      var e2 = t2.state, i2 = t2.options.element, n2 = void 0 === i2 ? "[data-popper-arrow]" : i2;
      null != n2 && ("string" != typeof n2 || (n2 = e2.elements.popper.querySelector(n2))) && Oe(e2.elements.popper, n2) && (e2.elements.arrow = n2);
    }, requires: ["popperOffsets"], requiresIfExists: ["preventOverflow"] };
    function Fe(t2) {
      return t2.split("-")[1];
    }
    var He = { top: "auto", right: "auto", bottom: "auto", left: "auto" };
    function We(t2) {
      var e2, i2 = t2.popper, n2 = t2.popperRect, s2 = t2.placement, o2 = t2.variation, r2 = t2.offsets, a2 = t2.position, l2 = t2.gpuAcceleration, c2 = t2.adaptive, h2 = t2.roundOffsets, d2 = t2.isFixed, u2 = r2.x, f2 = void 0 === u2 ? 0 : u2, p3 = r2.y, m4 = void 0 === p3 ? 0 : p3, g2 = "function" == typeof h2 ? h2({ x: f2, y: m4 }) : { x: f2, y: m4 };
      f2 = g2.x, m4 = g2.y;
      var _2 = r2.hasOwnProperty("x"), b2 = r2.hasOwnProperty("y"), v2 = Vt, y2 = zt, w2 = window;
      if (c2) {
        var A2 = $e(i2), E2 = "clientHeight", T2 = "clientWidth";
        A2 === fe(i2) && "static" !== xe(A2 = Le(i2)).position && "absolute" === a2 && (E2 = "scrollHeight", T2 = "scrollWidth"), (s2 === zt || (s2 === Vt || s2 === qt) && o2 === Yt) && (y2 = Rt, m4 -= (d2 && A2 === w2 && w2.visualViewport ? w2.visualViewport.height : A2[E2]) - n2.height, m4 *= l2 ? 1 : -1), s2 !== Vt && (s2 !== zt && s2 !== Rt || o2 !== Yt) || (v2 = qt, f2 -= (d2 && A2 === w2 && w2.visualViewport ? w2.visualViewport.width : A2[T2]) - n2.width, f2 *= l2 ? 1 : -1);
      }
      var C2, O2 = Object.assign({ position: a2 }, c2 && He), x2 = true === h2 ? function(t3, e3) {
        var i3 = t3.x, n3 = t3.y, s3 = e3.devicePixelRatio || 1;
        return { x: we(i3 * s3) / s3 || 0, y: we(n3 * s3) / s3 || 0 };
      }({ x: f2, y: m4 }, fe(i2)) : { x: f2, y: m4 };
      return f2 = x2.x, m4 = x2.y, l2 ? Object.assign({}, O2, ((C2 = {})[y2] = b2 ? "0" : "", C2[v2] = _2 ? "0" : "", C2.transform = (w2.devicePixelRatio || 1) <= 1 ? "translate(" + f2 + "px, " + m4 + "px)" : "translate3d(" + f2 + "px, " + m4 + "px, 0)", C2)) : Object.assign({}, O2, ((e2 = {})[y2] = b2 ? m4 + "px" : "", e2[v2] = _2 ? f2 + "px" : "", e2.transform = "", e2));
    }
    const Be = { name: "computeStyles", enabled: true, phase: "beforeWrite", fn: function(t2) {
      var e2 = t2.state, i2 = t2.options, n2 = i2.gpuAcceleration, s2 = void 0 === n2 || n2, o2 = i2.adaptive, r2 = void 0 === o2 || o2, a2 = i2.roundOffsets, l2 = void 0 === a2 || a2, c2 = { placement: be(e2.placement), variation: Fe(e2.placement), popper: e2.elements.popper, popperRect: e2.rects.popper, gpuAcceleration: s2, isFixed: "fixed" === e2.options.strategy };
      null != e2.modifiersData.popperOffsets && (e2.styles.popper = Object.assign({}, e2.styles.popper, We(Object.assign({}, c2, { offsets: e2.modifiersData.popperOffsets, position: e2.options.strategy, adaptive: r2, roundOffsets: l2 })))), null != e2.modifiersData.arrow && (e2.styles.arrow = Object.assign({}, e2.styles.arrow, We(Object.assign({}, c2, { offsets: e2.modifiersData.arrow, position: "absolute", adaptive: false, roundOffsets: l2 })))), e2.attributes.popper = Object.assign({}, e2.attributes.popper, { "data-popper-placement": e2.placement });
    }, data: {} };
    var ze = { passive: true };
    const Re = { name: "eventListeners", enabled: true, phase: "write", fn: function() {
    }, effect: function(t2) {
      var e2 = t2.state, i2 = t2.instance, n2 = t2.options, s2 = n2.scroll, o2 = void 0 === s2 || s2, r2 = n2.resize, a2 = void 0 === r2 || r2, l2 = fe(e2.elements.popper), c2 = [].concat(e2.scrollParents.reference, e2.scrollParents.popper);
      return o2 && c2.forEach(function(t3) {
        t3.addEventListener("scroll", i2.update, ze);
      }), a2 && l2.addEventListener("resize", i2.update, ze), function() {
        o2 && c2.forEach(function(t3) {
          t3.removeEventListener("scroll", i2.update, ze);
        }), a2 && l2.removeEventListener("resize", i2.update, ze);
      };
    }, data: {} };
    var qe = { left: "right", right: "left", bottom: "top", top: "bottom" };
    function Ve(t2) {
      return t2.replace(/left|right|bottom|top/g, function(t3) {
        return qe[t3];
      });
    }
    var Ke = { start: "end", end: "start" };
    function Qe(t2) {
      return t2.replace(/start|end/g, function(t3) {
        return Ke[t3];
      });
    }
    function Xe(t2) {
      var e2 = fe(t2);
      return { scrollLeft: e2.pageXOffset, scrollTop: e2.pageYOffset };
    }
    function Ye(t2) {
      return Te(Le(t2)).left + Xe(t2).scrollLeft;
    }
    function Ue(t2) {
      var e2 = xe(t2), i2 = e2.overflow, n2 = e2.overflowX, s2 = e2.overflowY;
      return /auto|scroll|overlay|hidden/.test(i2 + s2 + n2);
    }
    function Ge(t2) {
      return ["html", "body", "#document"].indexOf(ue(t2)) >= 0 ? t2.ownerDocument.body : me(t2) && Ue(t2) ? t2 : Ge(Se(t2));
    }
    function Je(t2, e2) {
      var i2;
      void 0 === e2 && (e2 = []);
      var n2 = Ge(t2), s2 = n2 === (null == (i2 = t2.ownerDocument) ? void 0 : i2.body), o2 = fe(n2), r2 = s2 ? [o2].concat(o2.visualViewport || [], Ue(n2) ? n2 : []) : n2, a2 = e2.concat(r2);
      return s2 ? a2 : a2.concat(Je(Se(r2)));
    }
    function Ze(t2) {
      return Object.assign({}, t2, { left: t2.x, top: t2.y, right: t2.x + t2.width, bottom: t2.y + t2.height });
    }
    function ti(t2, e2, i2) {
      return e2 === Gt ? Ze(function(t3, e3) {
        var i3 = fe(t3), n2 = Le(t3), s2 = i3.visualViewport, o2 = n2.clientWidth, r2 = n2.clientHeight, a2 = 0, l2 = 0;
        if (s2) {
          o2 = s2.width, r2 = s2.height;
          var c2 = Ee();
          (c2 || !c2 && "fixed" === e3) && (a2 = s2.offsetLeft, l2 = s2.offsetTop);
        }
        return { width: o2, height: r2, x: a2 + Ye(t3), y: l2 };
      }(t2, i2)) : pe(e2) ? function(t3, e3) {
        var i3 = Te(t3, false, "fixed" === e3);
        return i3.top = i3.top + t3.clientTop, i3.left = i3.left + t3.clientLeft, i3.bottom = i3.top + t3.clientHeight, i3.right = i3.left + t3.clientWidth, i3.width = t3.clientWidth, i3.height = t3.clientHeight, i3.x = i3.left, i3.y = i3.top, i3;
      }(e2, i2) : Ze(function(t3) {
        var e3, i3 = Le(t3), n2 = Xe(t3), s2 = null == (e3 = t3.ownerDocument) ? void 0 : e3.body, o2 = ve(i3.scrollWidth, i3.clientWidth, s2 ? s2.scrollWidth : 0, s2 ? s2.clientWidth : 0), r2 = ve(i3.scrollHeight, i3.clientHeight, s2 ? s2.scrollHeight : 0, s2 ? s2.clientHeight : 0), a2 = -n2.scrollLeft + Ye(t3), l2 = -n2.scrollTop;
        return "rtl" === xe(s2 || i3).direction && (a2 += ve(i3.clientWidth, s2 ? s2.clientWidth : 0) - o2), { width: o2, height: r2, x: a2, y: l2 };
      }(Le(t2)));
    }
    function ei(t2) {
      var e2, i2 = t2.reference, n2 = t2.element, s2 = t2.placement, o2 = s2 ? be(s2) : null, r2 = s2 ? Fe(s2) : null, a2 = i2.x + i2.width / 2 - n2.width / 2, l2 = i2.y + i2.height / 2 - n2.height / 2;
      switch (o2) {
        case zt:
          e2 = { x: a2, y: i2.y - n2.height };
          break;
        case Rt:
          e2 = { x: a2, y: i2.y + i2.height };
          break;
        case qt:
          e2 = { x: i2.x + i2.width, y: l2 };
          break;
        case Vt:
          e2 = { x: i2.x - n2.width, y: l2 };
          break;
        default:
          e2 = { x: i2.x, y: i2.y };
      }
      var c2 = o2 ? Ie(o2) : null;
      if (null != c2) {
        var h2 = "y" === c2 ? "height" : "width";
        switch (r2) {
          case Xt:
            e2[c2] = e2[c2] - (i2[h2] / 2 - n2[h2] / 2);
            break;
          case Yt:
            e2[c2] = e2[c2] + (i2[h2] / 2 - n2[h2] / 2);
        }
      }
      return e2;
    }
    function ii(t2, e2) {
      void 0 === e2 && (e2 = {});
      var i2 = e2, n2 = i2.placement, s2 = void 0 === n2 ? t2.placement : n2, o2 = i2.strategy, r2 = void 0 === o2 ? t2.strategy : o2, a2 = i2.boundary, l2 = void 0 === a2 ? Ut : a2, c2 = i2.rootBoundary, h2 = void 0 === c2 ? Gt : c2, d2 = i2.elementContext, u2 = void 0 === d2 ? Jt : d2, f2 = i2.altBoundary, p3 = void 0 !== f2 && f2, m4 = i2.padding, g2 = void 0 === m4 ? 0 : m4, _2 = Pe("number" != typeof g2 ? g2 : je(g2, Qt)), b2 = u2 === Jt ? Zt : Jt, v2 = t2.rects.popper, y2 = t2.elements[p3 ? b2 : u2], w2 = function(t3, e3, i3, n3) {
        var s3 = "clippingParents" === e3 ? function(t4) {
          var e4 = Je(Se(t4)), i4 = ["absolute", "fixed"].indexOf(xe(t4).position) >= 0 && me(t4) ? $e(t4) : t4;
          return pe(i4) ? e4.filter(function(t5) {
            return pe(t5) && Oe(t5, i4) && "body" !== ue(t5);
          }) : [];
        }(t3) : [].concat(e3), o3 = [].concat(s3, [i3]), r3 = o3[0], a3 = o3.reduce(function(e4, i4) {
          var s4 = ti(t3, i4, n3);
          return e4.top = ve(s4.top, e4.top), e4.right = ye(s4.right, e4.right), e4.bottom = ye(s4.bottom, e4.bottom), e4.left = ve(s4.left, e4.left), e4;
        }, ti(t3, r3, n3));
        return a3.width = a3.right - a3.left, a3.height = a3.bottom - a3.top, a3.x = a3.left, a3.y = a3.top, a3;
      }(pe(y2) ? y2 : y2.contextElement || Le(t2.elements.popper), l2, h2, r2), A2 = Te(t2.elements.reference), E2 = ei({ reference: A2, element: v2, strategy: "absolute", placement: s2 }), T2 = Ze(Object.assign({}, v2, E2)), C2 = u2 === Jt ? T2 : A2, O2 = { top: w2.top - C2.top + _2.top, bottom: C2.bottom - w2.bottom + _2.bottom, left: w2.left - C2.left + _2.left, right: C2.right - w2.right + _2.right }, x2 = t2.modifiersData.offset;
      if (u2 === Jt && x2) {
        var k2 = x2[s2];
        Object.keys(O2).forEach(function(t3) {
          var e3 = [qt, Rt].indexOf(t3) >= 0 ? 1 : -1, i3 = [zt, Rt].indexOf(t3) >= 0 ? "y" : "x";
          O2[t3] += k2[i3] * e3;
        });
      }
      return O2;
    }
    function ni(t2, e2) {
      void 0 === e2 && (e2 = {});
      var i2 = e2, n2 = i2.placement, s2 = i2.boundary, o2 = i2.rootBoundary, r2 = i2.padding, a2 = i2.flipVariations, l2 = i2.allowedAutoPlacements, c2 = void 0 === l2 ? ee : l2, h2 = Fe(n2), d2 = h2 ? a2 ? te : te.filter(function(t3) {
        return Fe(t3) === h2;
      }) : Qt, u2 = d2.filter(function(t3) {
        return c2.indexOf(t3) >= 0;
      });
      0 === u2.length && (u2 = d2);
      var f2 = u2.reduce(function(e3, i3) {
        return e3[i3] = ii(t2, { placement: i3, boundary: s2, rootBoundary: o2, padding: r2 })[be(i3)], e3;
      }, {});
      return Object.keys(f2).sort(function(t3, e3) {
        return f2[t3] - f2[e3];
      });
    }
    const si = { name: "flip", enabled: true, phase: "main", fn: function(t2) {
      var e2 = t2.state, i2 = t2.options, n2 = t2.name;
      if (!e2.modifiersData[n2]._skip) {
        for (var s2 = i2.mainAxis, o2 = void 0 === s2 || s2, r2 = i2.altAxis, a2 = void 0 === r2 || r2, l2 = i2.fallbackPlacements, c2 = i2.padding, h2 = i2.boundary, d2 = i2.rootBoundary, u2 = i2.altBoundary, f2 = i2.flipVariations, p3 = void 0 === f2 || f2, m4 = i2.allowedAutoPlacements, g2 = e2.options.placement, _2 = be(g2), b2 = l2 || (_2 !== g2 && p3 ? function(t3) {
          if (be(t3) === Kt)
            return [];
          var e3 = Ve(t3);
          return [Qe(t3), e3, Qe(e3)];
        }(g2) : [Ve(g2)]), v2 = [g2].concat(b2).reduce(function(t3, i3) {
          return t3.concat(be(i3) === Kt ? ni(e2, { placement: i3, boundary: h2, rootBoundary: d2, padding: c2, flipVariations: p3, allowedAutoPlacements: m4 }) : i3);
        }, []), y2 = e2.rects.reference, w2 = e2.rects.popper, A2 = /* @__PURE__ */ new Map(), E2 = true, T2 = v2[0], C2 = 0; C2 < v2.length; C2++) {
          var O2 = v2[C2], x2 = be(O2), k2 = Fe(O2) === Xt, L2 = [zt, Rt].indexOf(x2) >= 0, S2 = L2 ? "width" : "height", D2 = ii(e2, { placement: O2, boundary: h2, rootBoundary: d2, altBoundary: u2, padding: c2 }), $2 = L2 ? k2 ? qt : Vt : k2 ? Rt : zt;
          y2[S2] > w2[S2] && ($2 = Ve($2));
          var I2 = Ve($2), N2 = [];
          if (o2 && N2.push(D2[x2] <= 0), a2 && N2.push(D2[$2] <= 0, D2[I2] <= 0), N2.every(function(t3) {
            return t3;
          })) {
            T2 = O2, E2 = false;
            break;
          }
          A2.set(O2, N2);
        }
        if (E2)
          for (var P2 = function(t3) {
            var e3 = v2.find(function(e4) {
              var i3 = A2.get(e4);
              if (i3)
                return i3.slice(0, t3).every(function(t4) {
                  return t4;
                });
            });
            if (e3)
              return T2 = e3, "break";
          }, j2 = p3 ? 3 : 1; j2 > 0 && "break" !== P2(j2); j2--)
            ;
        e2.placement !== T2 && (e2.modifiersData[n2]._skip = true, e2.placement = T2, e2.reset = true);
      }
    }, requiresIfExists: ["offset"], data: { _skip: false } };
    function oi(t2, e2, i2) {
      return void 0 === i2 && (i2 = { x: 0, y: 0 }), { top: t2.top - e2.height - i2.y, right: t2.right - e2.width + i2.x, bottom: t2.bottom - e2.height + i2.y, left: t2.left - e2.width - i2.x };
    }
    function ri(t2) {
      return [zt, qt, Rt, Vt].some(function(e2) {
        return t2[e2] >= 0;
      });
    }
    const ai = { name: "hide", enabled: true, phase: "main", requiresIfExists: ["preventOverflow"], fn: function(t2) {
      var e2 = t2.state, i2 = t2.name, n2 = e2.rects.reference, s2 = e2.rects.popper, o2 = e2.modifiersData.preventOverflow, r2 = ii(e2, { elementContext: "reference" }), a2 = ii(e2, { altBoundary: true }), l2 = oi(r2, n2), c2 = oi(a2, s2, o2), h2 = ri(l2), d2 = ri(c2);
      e2.modifiersData[i2] = { referenceClippingOffsets: l2, popperEscapeOffsets: c2, isReferenceHidden: h2, hasPopperEscaped: d2 }, e2.attributes.popper = Object.assign({}, e2.attributes.popper, { "data-popper-reference-hidden": h2, "data-popper-escaped": d2 });
    } }, li = { name: "offset", enabled: true, phase: "main", requires: ["popperOffsets"], fn: function(t2) {
      var e2 = t2.state, i2 = t2.options, n2 = t2.name, s2 = i2.offset, o2 = void 0 === s2 ? [0, 0] : s2, r2 = ee.reduce(function(t3, i3) {
        return t3[i3] = function(t4, e3, i4) {
          var n3 = be(t4), s3 = [Vt, zt].indexOf(n3) >= 0 ? -1 : 1, o3 = "function" == typeof i4 ? i4(Object.assign({}, e3, { placement: t4 })) : i4, r3 = o3[0], a3 = o3[1];
          return r3 = r3 || 0, a3 = (a3 || 0) * s3, [Vt, qt].indexOf(n3) >= 0 ? { x: a3, y: r3 } : { x: r3, y: a3 };
        }(i3, e2.rects, o2), t3;
      }, {}), a2 = r2[e2.placement], l2 = a2.x, c2 = a2.y;
      null != e2.modifiersData.popperOffsets && (e2.modifiersData.popperOffsets.x += l2, e2.modifiersData.popperOffsets.y += c2), e2.modifiersData[n2] = r2;
    } }, ci = { name: "popperOffsets", enabled: true, phase: "read", fn: function(t2) {
      var e2 = t2.state, i2 = t2.name;
      e2.modifiersData[i2] = ei({ reference: e2.rects.reference, element: e2.rects.popper, strategy: "absolute", placement: e2.placement });
    }, data: {} }, hi = { name: "preventOverflow", enabled: true, phase: "main", fn: function(t2) {
      var e2 = t2.state, i2 = t2.options, n2 = t2.name, s2 = i2.mainAxis, o2 = void 0 === s2 || s2, r2 = i2.altAxis, a2 = void 0 !== r2 && r2, l2 = i2.boundary, c2 = i2.rootBoundary, h2 = i2.altBoundary, d2 = i2.padding, u2 = i2.tether, f2 = void 0 === u2 || u2, p3 = i2.tetherOffset, m4 = void 0 === p3 ? 0 : p3, g2 = ii(e2, { boundary: l2, rootBoundary: c2, padding: d2, altBoundary: h2 }), _2 = be(e2.placement), b2 = Fe(e2.placement), v2 = !b2, y2 = Ie(_2), w2 = "x" === y2 ? "y" : "x", A2 = e2.modifiersData.popperOffsets, E2 = e2.rects.reference, T2 = e2.rects.popper, C2 = "function" == typeof m4 ? m4(Object.assign({}, e2.rects, { placement: e2.placement })) : m4, O2 = "number" == typeof C2 ? { mainAxis: C2, altAxis: C2 } : Object.assign({ mainAxis: 0, altAxis: 0 }, C2), x2 = e2.modifiersData.offset ? e2.modifiersData.offset[e2.placement] : null, k2 = { x: 0, y: 0 };
      if (A2) {
        if (o2) {
          var L2, S2 = "y" === y2 ? zt : Vt, D2 = "y" === y2 ? Rt : qt, $2 = "y" === y2 ? "height" : "width", I2 = A2[y2], N2 = I2 + g2[S2], P2 = I2 - g2[D2], j2 = f2 ? -T2[$2] / 2 : 0, M2 = b2 === Xt ? E2[$2] : T2[$2], F2 = b2 === Xt ? -T2[$2] : -E2[$2], H2 = e2.elements.arrow, W2 = f2 && H2 ? Ce(H2) : { width: 0, height: 0 }, B2 = e2.modifiersData["arrow#persistent"] ? e2.modifiersData["arrow#persistent"].padding : { top: 0, right: 0, bottom: 0, left: 0 }, z2 = B2[S2], R2 = B2[D2], q2 = Ne(0, E2[$2], W2[$2]), V2 = v2 ? E2[$2] / 2 - j2 - q2 - z2 - O2.mainAxis : M2 - q2 - z2 - O2.mainAxis, K2 = v2 ? -E2[$2] / 2 + j2 + q2 + R2 + O2.mainAxis : F2 + q2 + R2 + O2.mainAxis, Q2 = e2.elements.arrow && $e(e2.elements.arrow), X2 = Q2 ? "y" === y2 ? Q2.clientTop || 0 : Q2.clientLeft || 0 : 0, Y2 = null != (L2 = null == x2 ? void 0 : x2[y2]) ? L2 : 0, U2 = I2 + K2 - Y2, G2 = Ne(f2 ? ye(N2, I2 + V2 - Y2 - X2) : N2, I2, f2 ? ve(P2, U2) : P2);
          A2[y2] = G2, k2[y2] = G2 - I2;
        }
        if (a2) {
          var J2, Z2 = "x" === y2 ? zt : Vt, tt2 = "x" === y2 ? Rt : qt, et2 = A2[w2], it2 = "y" === w2 ? "height" : "width", nt2 = et2 + g2[Z2], st2 = et2 - g2[tt2], ot2 = -1 !== [zt, Vt].indexOf(_2), rt2 = null != (J2 = null == x2 ? void 0 : x2[w2]) ? J2 : 0, at2 = ot2 ? nt2 : et2 - E2[it2] - T2[it2] - rt2 + O2.altAxis, lt2 = ot2 ? et2 + E2[it2] + T2[it2] - rt2 - O2.altAxis : st2, ct2 = f2 && ot2 ? function(t3, e3, i3) {
            var n3 = Ne(t3, e3, i3);
            return n3 > i3 ? i3 : n3;
          }(at2, et2, lt2) : Ne(f2 ? at2 : nt2, et2, f2 ? lt2 : st2);
          A2[w2] = ct2, k2[w2] = ct2 - et2;
        }
        e2.modifiersData[n2] = k2;
      }
    }, requiresIfExists: ["offset"] };
    function di(t2, e2, i2) {
      void 0 === i2 && (i2 = false);
      var n2, s2, o2 = me(e2), r2 = me(e2) && function(t3) {
        var e3 = t3.getBoundingClientRect(), i3 = we(e3.width) / t3.offsetWidth || 1, n3 = we(e3.height) / t3.offsetHeight || 1;
        return 1 !== i3 || 1 !== n3;
      }(e2), a2 = Le(e2), l2 = Te(t2, r2, i2), c2 = { scrollLeft: 0, scrollTop: 0 }, h2 = { x: 0, y: 0 };
      return (o2 || !o2 && !i2) && (("body" !== ue(e2) || Ue(a2)) && (c2 = (n2 = e2) !== fe(n2) && me(n2) ? { scrollLeft: (s2 = n2).scrollLeft, scrollTop: s2.scrollTop } : Xe(n2)), me(e2) ? ((h2 = Te(e2, true)).x += e2.clientLeft, h2.y += e2.clientTop) : a2 && (h2.x = Ye(a2))), { x: l2.left + c2.scrollLeft - h2.x, y: l2.top + c2.scrollTop - h2.y, width: l2.width, height: l2.height };
    }
    function ui(t2) {
      var e2 = /* @__PURE__ */ new Map(), i2 = /* @__PURE__ */ new Set(), n2 = [];
      function s2(t3) {
        i2.add(t3.name), [].concat(t3.requires || [], t3.requiresIfExists || []).forEach(function(t4) {
          if (!i2.has(t4)) {
            var n3 = e2.get(t4);
            n3 && s2(n3);
          }
        }), n2.push(t3);
      }
      return t2.forEach(function(t3) {
        e2.set(t3.name, t3);
      }), t2.forEach(function(t3) {
        i2.has(t3.name) || s2(t3);
      }), n2;
    }
    var fi = { placement: "bottom", modifiers: [], strategy: "absolute" };
    function pi() {
      for (var t2 = arguments.length, e2 = new Array(t2), i2 = 0; i2 < t2; i2++)
        e2[i2] = arguments[i2];
      return !e2.some(function(t3) {
        return !(t3 && "function" == typeof t3.getBoundingClientRect);
      });
    }
    function mi(t2) {
      void 0 === t2 && (t2 = {});
      var e2 = t2, i2 = e2.defaultModifiers, n2 = void 0 === i2 ? [] : i2, s2 = e2.defaultOptions, o2 = void 0 === s2 ? fi : s2;
      return function(t3, e3, i3) {
        void 0 === i3 && (i3 = o2);
        var s3, r2, a2 = { placement: "bottom", orderedModifiers: [], options: Object.assign({}, fi, o2), modifiersData: {}, elements: { reference: t3, popper: e3 }, attributes: {}, styles: {} }, l2 = [], c2 = false, h2 = { state: a2, setOptions: function(i4) {
          var s4 = "function" == typeof i4 ? i4(a2.options) : i4;
          d2(), a2.options = Object.assign({}, o2, a2.options, s4), a2.scrollParents = { reference: pe(t3) ? Je(t3) : t3.contextElement ? Je(t3.contextElement) : [], popper: Je(e3) };
          var r3, c3, u2 = function(t4) {
            var e4 = ui(t4);
            return de.reduce(function(t5, i5) {
              return t5.concat(e4.filter(function(t6) {
                return t6.phase === i5;
              }));
            }, []);
          }((r3 = [].concat(n2, a2.options.modifiers), c3 = r3.reduce(function(t4, e4) {
            var i5 = t4[e4.name];
            return t4[e4.name] = i5 ? Object.assign({}, i5, e4, { options: Object.assign({}, i5.options, e4.options), data: Object.assign({}, i5.data, e4.data) }) : e4, t4;
          }, {}), Object.keys(c3).map(function(t4) {
            return c3[t4];
          })));
          return a2.orderedModifiers = u2.filter(function(t4) {
            return t4.enabled;
          }), a2.orderedModifiers.forEach(function(t4) {
            var e4 = t4.name, i5 = t4.options, n3 = void 0 === i5 ? {} : i5, s5 = t4.effect;
            if ("function" == typeof s5) {
              var o3 = s5({ state: a2, name: e4, instance: h2, options: n3 });
              l2.push(o3 || function() {
              });
            }
          }), h2.update();
        }, forceUpdate: function() {
          if (!c2) {
            var t4 = a2.elements, e4 = t4.reference, i4 = t4.popper;
            if (pi(e4, i4)) {
              a2.rects = { reference: di(e4, $e(i4), "fixed" === a2.options.strategy), popper: Ce(i4) }, a2.reset = false, a2.placement = a2.options.placement, a2.orderedModifiers.forEach(function(t5) {
                return a2.modifiersData[t5.name] = Object.assign({}, t5.data);
              });
              for (var n3 = 0; n3 < a2.orderedModifiers.length; n3++)
                if (true !== a2.reset) {
                  var s4 = a2.orderedModifiers[n3], o3 = s4.fn, r3 = s4.options, l3 = void 0 === r3 ? {} : r3, d3 = s4.name;
                  "function" == typeof o3 && (a2 = o3({ state: a2, options: l3, name: d3, instance: h2 }) || a2);
                } else
                  a2.reset = false, n3 = -1;
            }
          }
        }, update: (s3 = function() {
          return new Promise(function(t4) {
            h2.forceUpdate(), t4(a2);
          });
        }, function() {
          return r2 || (r2 = new Promise(function(t4) {
            Promise.resolve().then(function() {
              r2 = void 0, t4(s3());
            });
          })), r2;
        }), destroy: function() {
          d2(), c2 = true;
        } };
        if (!pi(t3, e3))
          return h2;
        function d2() {
          l2.forEach(function(t4) {
            return t4();
          }), l2 = [];
        }
        return h2.setOptions(i3).then(function(t4) {
          !c2 && i3.onFirstUpdate && i3.onFirstUpdate(t4);
        }), h2;
      };
    }
    var gi = mi(), _i = mi({ defaultModifiers: [Re, ci, Be, _e] }), bi = mi({ defaultModifiers: [Re, ci, Be, _e, li, si, hi, Me, ai] });
    const vi = Object.freeze(Object.defineProperty({ __proto__: null, afterMain: ae, afterRead: se, afterWrite: he, applyStyles: _e, arrow: Me, auto: Kt, basePlacements: Qt, beforeMain: oe, beforeRead: ie, beforeWrite: le, bottom: Rt, clippingParents: Ut, computeStyles: Be, createPopper: bi, createPopperBase: gi, createPopperLite: _i, detectOverflow: ii, end: Yt, eventListeners: Re, flip: si, hide: ai, left: Vt, main: re, modifierPhases: de, offset: li, placements: ee, popper: Jt, popperGenerator: mi, popperOffsets: ci, preventOverflow: hi, read: ne, reference: Zt, right: qt, start: Xt, top: zt, variationPlacements: te, viewport: Gt, write: ce }, Symbol.toStringTag, { value: "Module" })), yi = "dropdown", wi = ".bs.dropdown", Ai = ".data-api", Ei = "ArrowUp", Ti = "ArrowDown", Ci = `hide${wi}`, Oi = `hidden${wi}`, xi = `show${wi}`, ki = `shown${wi}`, Li = `click${wi}${Ai}`, Si = `keydown${wi}${Ai}`, Di = `keyup${wi}${Ai}`, $i = "show", Ii = '[data-bs-toggle="dropdown"]:not(.disabled):not(:disabled)', Ni = `${Ii}.${$i}`, Pi = ".dropdown-menu", ji = p2() ? "top-end" : "top-start", Mi = p2() ? "top-start" : "top-end", Fi = p2() ? "bottom-end" : "bottom-start", Hi = p2() ? "bottom-start" : "bottom-end", Wi = p2() ? "left-start" : "right-start", Bi = p2() ? "right-start" : "left-start", zi = { autoClose: true, boundary: "clippingParents", display: "dynamic", offset: [0, 2], popperConfig: null, reference: "toggle" }, Ri = { autoClose: "(boolean|string)", boundary: "(string|element)", display: "string", offset: "(array|string|function)", popperConfig: "(null|object|function)", reference: "(string|element|object)" };
    class qi extends W {
      constructor(t2, e2) {
        super(t2, e2), this._popper = null, this._parent = this._element.parentNode, this._menu = z.next(this._element, Pi)[0] || z.prev(this._element, Pi)[0] || z.findOne(Pi, this._parent), this._inNavbar = this._detectNavbar();
      }
      static get Default() {
        return zi;
      }
      static get DefaultType() {
        return Ri;
      }
      static get NAME() {
        return yi;
      }
      toggle() {
        return this._isShown() ? this.hide() : this.show();
      }
      show() {
        if (l(this._element) || this._isShown())
          return;
        const t2 = { relatedTarget: this._element };
        if (!N.trigger(this._element, xi, t2).defaultPrevented) {
          if (this._createPopper(), "ontouchstart" in document.documentElement && !this._parent.closest(".navbar-nav"))
            for (const t3 of [].concat(...document.body.children))
              N.on(t3, "mouseover", h);
          this._element.focus(), this._element.setAttribute("aria-expanded", true), this._menu.classList.add($i), this._element.classList.add($i), N.trigger(this._element, ki, t2);
        }
      }
      hide() {
        if (l(this._element) || !this._isShown())
          return;
        const t2 = { relatedTarget: this._element };
        this._completeHide(t2);
      }
      dispose() {
        this._popper && this._popper.destroy(), super.dispose();
      }
      update() {
        this._inNavbar = this._detectNavbar(), this._popper && this._popper.update();
      }
      _completeHide(t2) {
        if (!N.trigger(this._element, Ci, t2).defaultPrevented) {
          if ("ontouchstart" in document.documentElement)
            for (const t3 of [].concat(...document.body.children))
              N.off(t3, "mouseover", h);
          this._popper && this._popper.destroy(), this._menu.classList.remove($i), this._element.classList.remove($i), this._element.setAttribute("aria-expanded", "false"), F.removeDataAttribute(this._menu, "popper"), N.trigger(this._element, Oi, t2);
        }
      }
      _getConfig(t2) {
        if ("object" == typeof (t2 = super._getConfig(t2)).reference && !o(t2.reference) && "function" != typeof t2.reference.getBoundingClientRect)
          throw new TypeError(`${yi.toUpperCase()}: Option "reference" provided type "object" without a required "getBoundingClientRect" method.`);
        return t2;
      }
      _createPopper() {
        if (void 0 === vi)
          throw new TypeError("Bootstrap's dropdowns require Popper (https://popper.js.org)");
        let t2 = this._element;
        "parent" === this._config.reference ? t2 = this._parent : o(this._config.reference) ? t2 = r(this._config.reference) : "object" == typeof this._config.reference && (t2 = this._config.reference);
        const e2 = this._getPopperConfig();
        this._popper = bi(t2, this._menu, e2);
      }
      _isShown() {
        return this._menu.classList.contains($i);
      }
      _getPlacement() {
        const t2 = this._parent;
        if (t2.classList.contains("dropend"))
          return Wi;
        if (t2.classList.contains("dropstart"))
          return Bi;
        if (t2.classList.contains("dropup-center"))
          return "top";
        if (t2.classList.contains("dropdown-center"))
          return "bottom";
        const e2 = "end" === getComputedStyle(this._menu).getPropertyValue("--bs-position").trim();
        return t2.classList.contains("dropup") ? e2 ? Mi : ji : e2 ? Hi : Fi;
      }
      _detectNavbar() {
        return null !== this._element.closest(".navbar");
      }
      _getOffset() {
        const { offset: t2 } = this._config;
        return "string" == typeof t2 ? t2.split(",").map((t3) => Number.parseInt(t3, 10)) : "function" == typeof t2 ? (e2) => t2(e2, this._element) : t2;
      }
      _getPopperConfig() {
        const t2 = { placement: this._getPlacement(), modifiers: [{ name: "preventOverflow", options: { boundary: this._config.boundary } }, { name: "offset", options: { offset: this._getOffset() } }] };
        return (this._inNavbar || "static" === this._config.display) && (F.setDataAttribute(this._menu, "popper", "static"), t2.modifiers = [{ name: "applyStyles", enabled: false }]), { ...t2, ...g(this._config.popperConfig, [t2]) };
      }
      _selectMenuItem({ key: t2, target: e2 }) {
        const i2 = z.find(".dropdown-menu .dropdown-item:not(.disabled):not(:disabled)", this._menu).filter((t3) => a(t3));
        i2.length && b(i2, e2, t2 === Ti, !i2.includes(e2)).focus();
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = qi.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2])
              throw new TypeError(`No method named "${t2}"`);
            e2[t2]();
          }
        });
      }
      static clearMenus(t2) {
        if (2 === t2.button || "keyup" === t2.type && "Tab" !== t2.key)
          return;
        const e2 = z.find(Ni);
        for (const i2 of e2) {
          const e3 = qi.getInstance(i2);
          if (!e3 || false === e3._config.autoClose)
            continue;
          const n2 = t2.composedPath(), s2 = n2.includes(e3._menu);
          if (n2.includes(e3._element) || "inside" === e3._config.autoClose && !s2 || "outside" === e3._config.autoClose && s2)
            continue;
          if (e3._menu.contains(t2.target) && ("keyup" === t2.type && "Tab" === t2.key || /input|select|option|textarea|form/i.test(t2.target.tagName)))
            continue;
          const o2 = { relatedTarget: e3._element };
          "click" === t2.type && (o2.clickEvent = t2), e3._completeHide(o2);
        }
      }
      static dataApiKeydownHandler(t2) {
        const e2 = /input|textarea/i.test(t2.target.tagName), i2 = "Escape" === t2.key, n2 = [Ei, Ti].includes(t2.key);
        if (!n2 && !i2)
          return;
        if (e2 && !i2)
          return;
        t2.preventDefault();
        const s2 = this.matches(Ii) ? this : z.prev(this, Ii)[0] || z.next(this, Ii)[0] || z.findOne(Ii, t2.delegateTarget.parentNode), o2 = qi.getOrCreateInstance(s2);
        if (n2)
          return t2.stopPropagation(), o2.show(), void o2._selectMenuItem(t2);
        o2._isShown() && (t2.stopPropagation(), o2.hide(), s2.focus());
      }
    }
    N.on(document, Si, Ii, qi.dataApiKeydownHandler), N.on(document, Si, Pi, qi.dataApiKeydownHandler), N.on(document, Li, qi.clearMenus), N.on(document, Di, qi.clearMenus), N.on(document, Li, Ii, function(t2) {
      t2.preventDefault(), qi.getOrCreateInstance(this).toggle();
    }), m3(qi);
    const Vi = "backdrop", Ki = "show", Qi = `mousedown.bs.${Vi}`, Xi = { className: "modal-backdrop", clickCallback: null, isAnimated: false, isVisible: true, rootElement: "body" }, Yi = { className: "string", clickCallback: "(function|null)", isAnimated: "boolean", isVisible: "boolean", rootElement: "(element|string)" };
    class Ui extends H {
      constructor(t2) {
        super(), this._config = this._getConfig(t2), this._isAppended = false, this._element = null;
      }
      static get Default() {
        return Xi;
      }
      static get DefaultType() {
        return Yi;
      }
      static get NAME() {
        return Vi;
      }
      show(t2) {
        if (!this._config.isVisible)
          return void g(t2);
        this._append();
        const e2 = this._getElement();
        this._config.isAnimated && d(e2), e2.classList.add(Ki), this._emulateAnimation(() => {
          g(t2);
        });
      }
      hide(t2) {
        this._config.isVisible ? (this._getElement().classList.remove(Ki), this._emulateAnimation(() => {
          this.dispose(), g(t2);
        })) : g(t2);
      }
      dispose() {
        this._isAppended && (N.off(this._element, Qi), this._element.remove(), this._isAppended = false);
      }
      _getElement() {
        if (!this._element) {
          const t2 = document.createElement("div");
          t2.className = this._config.className, this._config.isAnimated && t2.classList.add("fade"), this._element = t2;
        }
        return this._element;
      }
      _configAfterMerge(t2) {
        return t2.rootElement = r(t2.rootElement), t2;
      }
      _append() {
        if (this._isAppended)
          return;
        const t2 = this._getElement();
        this._config.rootElement.append(t2), N.on(t2, Qi, () => {
          g(this._config.clickCallback);
        }), this._isAppended = true;
      }
      _emulateAnimation(t2) {
        _(t2, this._getElement(), this._config.isAnimated);
      }
    }
    const Gi = ".bs.focustrap", Ji = `focusin${Gi}`, Zi = `keydown.tab${Gi}`, tn = "backward", en = { autofocus: true, trapElement: null }, nn = { autofocus: "boolean", trapElement: "element" };
    class sn extends H {
      constructor(t2) {
        super(), this._config = this._getConfig(t2), this._isActive = false, this._lastTabNavDirection = null;
      }
      static get Default() {
        return en;
      }
      static get DefaultType() {
        return nn;
      }
      static get NAME() {
        return "focustrap";
      }
      activate() {
        this._isActive || (this._config.autofocus && this._config.trapElement.focus(), N.off(document, Gi), N.on(document, Ji, (t2) => this._handleFocusin(t2)), N.on(document, Zi, (t2) => this._handleKeydown(t2)), this._isActive = true);
      }
      deactivate() {
        this._isActive && (this._isActive = false, N.off(document, Gi));
      }
      _handleFocusin(t2) {
        const { trapElement: e2 } = this._config;
        if (t2.target === document || t2.target === e2 || e2.contains(t2.target))
          return;
        const i2 = z.focusableChildren(e2);
        0 === i2.length ? e2.focus() : this._lastTabNavDirection === tn ? i2[i2.length - 1].focus() : i2[0].focus();
      }
      _handleKeydown(t2) {
        "Tab" === t2.key && (this._lastTabNavDirection = t2.shiftKey ? tn : "forward");
      }
    }
    const on = ".fixed-top, .fixed-bottom, .is-fixed, .sticky-top", rn = ".sticky-top", an = "padding-right", ln = "margin-right";
    class cn {
      constructor() {
        this._element = document.body;
      }
      getWidth() {
        const t2 = document.documentElement.clientWidth;
        return Math.abs(window.innerWidth - t2);
      }
      hide() {
        const t2 = this.getWidth();
        this._disableOverFlow(), this._setElementAttributes(this._element, an, (e2) => e2 + t2), this._setElementAttributes(on, an, (e2) => e2 + t2), this._setElementAttributes(rn, ln, (e2) => e2 - t2);
      }
      reset() {
        this._resetElementAttributes(this._element, "overflow"), this._resetElementAttributes(this._element, an), this._resetElementAttributes(on, an), this._resetElementAttributes(rn, ln);
      }
      isOverflowing() {
        return this.getWidth() > 0;
      }
      _disableOverFlow() {
        this._saveInitialAttribute(this._element, "overflow"), this._element.style.overflow = "hidden";
      }
      _setElementAttributes(t2, e2, i2) {
        const n2 = this.getWidth();
        this._applyManipulationCallback(t2, (t3) => {
          if (t3 !== this._element && window.innerWidth > t3.clientWidth + n2)
            return;
          this._saveInitialAttribute(t3, e2);
          const s2 = window.getComputedStyle(t3).getPropertyValue(e2);
          t3.style.setProperty(e2, `${i2(Number.parseFloat(s2))}px`);
        });
      }
      _saveInitialAttribute(t2, e2) {
        const i2 = t2.style.getPropertyValue(e2);
        i2 && F.setDataAttribute(t2, e2, i2);
      }
      _resetElementAttributes(t2, e2) {
        this._applyManipulationCallback(t2, (t3) => {
          const i2 = F.getDataAttribute(t3, e2);
          null !== i2 ? (F.removeDataAttribute(t3, e2), t3.style.setProperty(e2, i2)) : t3.style.removeProperty(e2);
        });
      }
      _applyManipulationCallback(t2, e2) {
        if (o(t2))
          e2(t2);
        else
          for (const i2 of z.find(t2, this._element))
            e2(i2);
      }
    }
    const hn = ".bs.modal", dn = `hide${hn}`, un = `hidePrevented${hn}`, fn = `hidden${hn}`, pn = `show${hn}`, mn = `shown${hn}`, gn = `resize${hn}`, _n = `click.dismiss${hn}`, bn = `mousedown.dismiss${hn}`, vn = `keydown.dismiss${hn}`, yn = `click${hn}.data-api`, wn = "modal-open", An = "show", En = "modal-static", Tn = { backdrop: true, focus: true, keyboard: true }, Cn = { backdrop: "(boolean|string)", focus: "boolean", keyboard: "boolean" };
    class On extends W {
      constructor(t2, e2) {
        super(t2, e2), this._dialog = z.findOne(".modal-dialog", this._element), this._backdrop = this._initializeBackDrop(), this._focustrap = this._initializeFocusTrap(), this._isShown = false, this._isTransitioning = false, this._scrollBar = new cn(), this._addEventListeners();
      }
      static get Default() {
        return Tn;
      }
      static get DefaultType() {
        return Cn;
      }
      static get NAME() {
        return "modal";
      }
      toggle(t2) {
        return this._isShown ? this.hide() : this.show(t2);
      }
      show(t2) {
        this._isShown || this._isTransitioning || N.trigger(this._element, pn, { relatedTarget: t2 }).defaultPrevented || (this._isShown = true, this._isTransitioning = true, this._scrollBar.hide(), document.body.classList.add(wn), this._adjustDialog(), this._backdrop.show(() => this._showElement(t2)));
      }
      hide() {
        this._isShown && !this._isTransitioning && (N.trigger(this._element, dn).defaultPrevented || (this._isShown = false, this._isTransitioning = true, this._focustrap.deactivate(), this._element.classList.remove(An), this._queueCallback(() => this._hideModal(), this._element, this._isAnimated())));
      }
      dispose() {
        N.off(window, hn), N.off(this._dialog, hn), this._backdrop.dispose(), this._focustrap.deactivate(), super.dispose();
      }
      handleUpdate() {
        this._adjustDialog();
      }
      _initializeBackDrop() {
        return new Ui({ isVisible: Boolean(this._config.backdrop), isAnimated: this._isAnimated() });
      }
      _initializeFocusTrap() {
        return new sn({ trapElement: this._element });
      }
      _showElement(t2) {
        document.body.contains(this._element) || document.body.append(this._element), this._element.style.display = "block", this._element.removeAttribute("aria-hidden"), this._element.setAttribute("aria-modal", true), this._element.setAttribute("role", "dialog"), this._element.scrollTop = 0;
        const e2 = z.findOne(".modal-body", this._dialog);
        e2 && (e2.scrollTop = 0), d(this._element), this._element.classList.add(An), this._queueCallback(() => {
          this._config.focus && this._focustrap.activate(), this._isTransitioning = false, N.trigger(this._element, mn, { relatedTarget: t2 });
        }, this._dialog, this._isAnimated());
      }
      _addEventListeners() {
        N.on(this._element, vn, (t2) => {
          "Escape" === t2.key && (this._config.keyboard ? this.hide() : this._triggerBackdropTransition());
        }), N.on(window, gn, () => {
          this._isShown && !this._isTransitioning && this._adjustDialog();
        }), N.on(this._element, bn, (t2) => {
          N.one(this._element, _n, (e2) => {
            this._element === t2.target && this._element === e2.target && ("static" !== this._config.backdrop ? this._config.backdrop && this.hide() : this._triggerBackdropTransition());
          });
        });
      }
      _hideModal() {
        this._element.style.display = "none", this._element.setAttribute("aria-hidden", true), this._element.removeAttribute("aria-modal"), this._element.removeAttribute("role"), this._isTransitioning = false, this._backdrop.hide(() => {
          document.body.classList.remove(wn), this._resetAdjustments(), this._scrollBar.reset(), N.trigger(this._element, fn);
        });
      }
      _isAnimated() {
        return this._element.classList.contains("fade");
      }
      _triggerBackdropTransition() {
        if (N.trigger(this._element, un).defaultPrevented)
          return;
        const t2 = this._element.scrollHeight > document.documentElement.clientHeight, e2 = this._element.style.overflowY;
        "hidden" === e2 || this._element.classList.contains(En) || (t2 || (this._element.style.overflowY = "hidden"), this._element.classList.add(En), this._queueCallback(() => {
          this._element.classList.remove(En), this._queueCallback(() => {
            this._element.style.overflowY = e2;
          }, this._dialog);
        }, this._dialog), this._element.focus());
      }
      _adjustDialog() {
        const t2 = this._element.scrollHeight > document.documentElement.clientHeight, e2 = this._scrollBar.getWidth(), i2 = e2 > 0;
        if (i2 && !t2) {
          const t3 = p2() ? "paddingLeft" : "paddingRight";
          this._element.style[t3] = `${e2}px`;
        }
        if (!i2 && t2) {
          const t3 = p2() ? "paddingRight" : "paddingLeft";
          this._element.style[t3] = `${e2}px`;
        }
      }
      _resetAdjustments() {
        this._element.style.paddingLeft = "", this._element.style.paddingRight = "";
      }
      static jQueryInterface(t2, e2) {
        return this.each(function() {
          const i2 = On.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === i2[t2])
              throw new TypeError(`No method named "${t2}"`);
            i2[t2](e2);
          }
        });
      }
    }
    N.on(document, yn, '[data-bs-toggle="modal"]', function(t2) {
      const e2 = z.getElementFromSelector(this);
      ["A", "AREA"].includes(this.tagName) && t2.preventDefault(), N.one(e2, pn, (t3) => {
        t3.defaultPrevented || N.one(e2, fn, () => {
          a(this) && this.focus();
        });
      });
      const i2 = z.findOne(".modal.show");
      i2 && On.getInstance(i2).hide(), On.getOrCreateInstance(e2).toggle(this);
    }), R(On), m3(On);
    const xn = ".bs.offcanvas", kn = ".data-api", Ln = `load${xn}${kn}`, Sn = "show", Dn = "showing", $n = "hiding", In = ".offcanvas.show", Nn = `show${xn}`, Pn = `shown${xn}`, jn = `hide${xn}`, Mn = `hidePrevented${xn}`, Fn = `hidden${xn}`, Hn = `resize${xn}`, Wn = `click${xn}${kn}`, Bn = `keydown.dismiss${xn}`, zn = { backdrop: true, keyboard: true, scroll: false }, Rn = { backdrop: "(boolean|string)", keyboard: "boolean", scroll: "boolean" };
    class qn extends W {
      constructor(t2, e2) {
        super(t2, e2), this._isShown = false, this._backdrop = this._initializeBackDrop(), this._focustrap = this._initializeFocusTrap(), this._addEventListeners();
      }
      static get Default() {
        return zn;
      }
      static get DefaultType() {
        return Rn;
      }
      static get NAME() {
        return "offcanvas";
      }
      toggle(t2) {
        return this._isShown ? this.hide() : this.show(t2);
      }
      show(t2) {
        this._isShown || N.trigger(this._element, Nn, { relatedTarget: t2 }).defaultPrevented || (this._isShown = true, this._backdrop.show(), this._config.scroll || new cn().hide(), this._element.setAttribute("aria-modal", true), this._element.setAttribute("role", "dialog"), this._element.classList.add(Dn), this._queueCallback(() => {
          this._config.scroll && !this._config.backdrop || this._focustrap.activate(), this._element.classList.add(Sn), this._element.classList.remove(Dn), N.trigger(this._element, Pn, { relatedTarget: t2 });
        }, this._element, true));
      }
      hide() {
        this._isShown && (N.trigger(this._element, jn).defaultPrevented || (this._focustrap.deactivate(), this._element.blur(), this._isShown = false, this._element.classList.add($n), this._backdrop.hide(), this._queueCallback(() => {
          this._element.classList.remove(Sn, $n), this._element.removeAttribute("aria-modal"), this._element.removeAttribute("role"), this._config.scroll || new cn().reset(), N.trigger(this._element, Fn);
        }, this._element, true)));
      }
      dispose() {
        this._backdrop.dispose(), this._focustrap.deactivate(), super.dispose();
      }
      _initializeBackDrop() {
        const t2 = Boolean(this._config.backdrop);
        return new Ui({ className: "offcanvas-backdrop", isVisible: t2, isAnimated: true, rootElement: this._element.parentNode, clickCallback: t2 ? () => {
          "static" !== this._config.backdrop ? this.hide() : N.trigger(this._element, Mn);
        } : null });
      }
      _initializeFocusTrap() {
        return new sn({ trapElement: this._element });
      }
      _addEventListeners() {
        N.on(this._element, Bn, (t2) => {
          "Escape" === t2.key && (this._config.keyboard ? this.hide() : N.trigger(this._element, Mn));
        });
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = qn.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2] || t2.startsWith("_") || "constructor" === t2)
              throw new TypeError(`No method named "${t2}"`);
            e2[t2](this);
          }
        });
      }
    }
    N.on(document, Wn, '[data-bs-toggle="offcanvas"]', function(t2) {
      const e2 = z.getElementFromSelector(this);
      if (["A", "AREA"].includes(this.tagName) && t2.preventDefault(), l(this))
        return;
      N.one(e2, Fn, () => {
        a(this) && this.focus();
      });
      const i2 = z.findOne(In);
      i2 && i2 !== e2 && qn.getInstance(i2).hide(), qn.getOrCreateInstance(e2).toggle(this);
    }), N.on(window, Ln, () => {
      for (const t2 of z.find(In))
        qn.getOrCreateInstance(t2).show();
    }), N.on(window, Hn, () => {
      for (const t2 of z.find("[aria-modal][class*=show][class*=offcanvas-]"))
        "fixed" !== getComputedStyle(t2).position && qn.getOrCreateInstance(t2).hide();
    }), R(qn), m3(qn);
    const Vn = { "*": ["class", "dir", "id", "lang", "role", /^aria-[\w-]*$/i], a: ["target", "href", "title", "rel"], area: [], b: [], br: [], col: [], code: [], dd: [], div: [], dl: [], dt: [], em: [], hr: [], h1: [], h2: [], h3: [], h4: [], h5: [], h6: [], i: [], img: ["src", "srcset", "alt", "title", "width", "height"], li: [], ol: [], p: [], pre: [], s: [], small: [], span: [], sub: [], sup: [], strong: [], u: [], ul: [] }, Kn = /* @__PURE__ */ new Set(["background", "cite", "href", "itemtype", "longdesc", "poster", "src", "xlink:href"]), Qn = /^(?!javascript:)(?:[a-z0-9+.-]+:|[^&:/?#]*(?:[/?#]|$))/i, Xn = (t2, e2) => {
      const i2 = t2.nodeName.toLowerCase();
      return e2.includes(i2) ? !Kn.has(i2) || Boolean(Qn.test(t2.nodeValue)) : e2.filter((t3) => t3 instanceof RegExp).some((t3) => t3.test(i2));
    }, Yn = { allowList: Vn, content: {}, extraClass: "", html: false, sanitize: true, sanitizeFn: null, template: "<div></div>" }, Un = { allowList: "object", content: "object", extraClass: "(string|function)", html: "boolean", sanitize: "boolean", sanitizeFn: "(null|function)", template: "string" }, Gn = { entry: "(string|element|function|null)", selector: "(string|element)" };
    class Jn extends H {
      constructor(t2) {
        super(), this._config = this._getConfig(t2);
      }
      static get Default() {
        return Yn;
      }
      static get DefaultType() {
        return Un;
      }
      static get NAME() {
        return "TemplateFactory";
      }
      getContent() {
        return Object.values(this._config.content).map((t2) => this._resolvePossibleFunction(t2)).filter(Boolean);
      }
      hasContent() {
        return this.getContent().length > 0;
      }
      changeContent(t2) {
        return this._checkContent(t2), this._config.content = { ...this._config.content, ...t2 }, this;
      }
      toHtml() {
        const t2 = document.createElement("div");
        t2.innerHTML = this._maybeSanitize(this._config.template);
        for (const [e3, i3] of Object.entries(this._config.content))
          this._setContent(t2, i3, e3);
        const e2 = t2.children[0], i2 = this._resolvePossibleFunction(this._config.extraClass);
        return i2 && e2.classList.add(...i2.split(" ")), e2;
      }
      _typeCheckConfig(t2) {
        super._typeCheckConfig(t2), this._checkContent(t2.content);
      }
      _checkContent(t2) {
        for (const [e2, i2] of Object.entries(t2))
          super._typeCheckConfig({ selector: e2, entry: i2 }, Gn);
      }
      _setContent(t2, e2, i2) {
        const n2 = z.findOne(i2, t2);
        n2 && ((e2 = this._resolvePossibleFunction(e2)) ? o(e2) ? this._putElementInTemplate(r(e2), n2) : this._config.html ? n2.innerHTML = this._maybeSanitize(e2) : n2.textContent = e2 : n2.remove());
      }
      _maybeSanitize(t2) {
        return this._config.sanitize ? function(t3, e2, i2) {
          if (!t3.length)
            return t3;
          if (i2 && "function" == typeof i2)
            return i2(t3);
          const n2 = new window.DOMParser().parseFromString(t3, "text/html"), s2 = [].concat(...n2.body.querySelectorAll("*"));
          for (const t4 of s2) {
            const i3 = t4.nodeName.toLowerCase();
            if (!Object.keys(e2).includes(i3)) {
              t4.remove();
              continue;
            }
            const n3 = [].concat(...t4.attributes), s3 = [].concat(e2["*"] || [], e2[i3] || []);
            for (const e3 of n3)
              Xn(e3, s3) || t4.removeAttribute(e3.nodeName);
          }
          return n2.body.innerHTML;
        }(t2, this._config.allowList, this._config.sanitizeFn) : t2;
      }
      _resolvePossibleFunction(t2) {
        return g(t2, [this]);
      }
      _putElementInTemplate(t2, e2) {
        if (this._config.html)
          return e2.innerHTML = "", void e2.append(t2);
        e2.textContent = t2.textContent;
      }
    }
    const Zn = /* @__PURE__ */ new Set(["sanitize", "allowList", "sanitizeFn"]), ts = "fade", es = "show", is = ".modal", ns = "hide.bs.modal", ss = "hover", os = "focus", rs = { AUTO: "auto", TOP: "top", RIGHT: p2() ? "left" : "right", BOTTOM: "bottom", LEFT: p2() ? "right" : "left" }, as = { allowList: Vn, animation: true, boundary: "clippingParents", container: false, customClass: "", delay: 0, fallbackPlacements: ["top", "right", "bottom", "left"], html: false, offset: [0, 6], placement: "top", popperConfig: null, sanitize: true, sanitizeFn: null, selector: false, template: '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>', title: "", trigger: "hover focus" }, ls = { allowList: "object", animation: "boolean", boundary: "(string|element)", container: "(string|element|boolean)", customClass: "(string|function)", delay: "(number|object)", fallbackPlacements: "array", html: "boolean", offset: "(array|string|function)", placement: "(string|function)", popperConfig: "(null|object|function)", sanitize: "boolean", sanitizeFn: "(null|function)", selector: "(string|boolean)", template: "string", title: "(string|element|function)", trigger: "string" };
    class cs extends W {
      constructor(t2, e2) {
        if (void 0 === vi)
          throw new TypeError("Bootstrap's tooltips require Popper (https://popper.js.org)");
        super(t2, e2), this._isEnabled = true, this._timeout = 0, this._isHovered = null, this._activeTrigger = {}, this._popper = null, this._templateFactory = null, this._newContent = null, this.tip = null, this._setListeners(), this._config.selector || this._fixTitle();
      }
      static get Default() {
        return as;
      }
      static get DefaultType() {
        return ls;
      }
      static get NAME() {
        return "tooltip";
      }
      enable() {
        this._isEnabled = true;
      }
      disable() {
        this._isEnabled = false;
      }
      toggleEnabled() {
        this._isEnabled = !this._isEnabled;
      }
      toggle() {
        this._isEnabled && (this._activeTrigger.click = !this._activeTrigger.click, this._isShown() ? this._leave() : this._enter());
      }
      dispose() {
        clearTimeout(this._timeout), N.off(this._element.closest(is), ns, this._hideModalHandler), this._element.getAttribute("data-bs-original-title") && this._element.setAttribute("title", this._element.getAttribute("data-bs-original-title")), this._disposePopper(), super.dispose();
      }
      show() {
        if ("none" === this._element.style.display)
          throw new Error("Please use show on visible elements");
        if (!this._isWithContent() || !this._isEnabled)
          return;
        const t2 = N.trigger(this._element, this.constructor.eventName("show")), e2 = (c(this._element) || this._element.ownerDocument.documentElement).contains(this._element);
        if (t2.defaultPrevented || !e2)
          return;
        this._disposePopper();
        const i2 = this._getTipElement();
        this._element.setAttribute("aria-describedby", i2.getAttribute("id"));
        const { container: n2 } = this._config;
        if (this._element.ownerDocument.documentElement.contains(this.tip) || (n2.append(i2), N.trigger(this._element, this.constructor.eventName("inserted"))), this._popper = this._createPopper(i2), i2.classList.add(es), "ontouchstart" in document.documentElement)
          for (const t3 of [].concat(...document.body.children))
            N.on(t3, "mouseover", h);
        this._queueCallback(() => {
          N.trigger(this._element, this.constructor.eventName("shown")), false === this._isHovered && this._leave(), this._isHovered = false;
        }, this.tip, this._isAnimated());
      }
      hide() {
        if (this._isShown() && !N.trigger(this._element, this.constructor.eventName("hide")).defaultPrevented) {
          if (this._getTipElement().classList.remove(es), "ontouchstart" in document.documentElement)
            for (const t2 of [].concat(...document.body.children))
              N.off(t2, "mouseover", h);
          this._activeTrigger.click = false, this._activeTrigger[os] = false, this._activeTrigger[ss] = false, this._isHovered = null, this._queueCallback(() => {
            this._isWithActiveTrigger() || (this._isHovered || this._disposePopper(), this._element.removeAttribute("aria-describedby"), N.trigger(this._element, this.constructor.eventName("hidden")));
          }, this.tip, this._isAnimated());
        }
      }
      update() {
        this._popper && this._popper.update();
      }
      _isWithContent() {
        return Boolean(this._getTitle());
      }
      _getTipElement() {
        return this.tip || (this.tip = this._createTipElement(this._newContent || this._getContentForTemplate())), this.tip;
      }
      _createTipElement(t2) {
        const e2 = this._getTemplateFactory(t2).toHtml();
        if (!e2)
          return null;
        e2.classList.remove(ts, es), e2.classList.add(`bs-${this.constructor.NAME}-auto`);
        const i2 = ((t3) => {
          do {
            t3 += Math.floor(1e6 * Math.random());
          } while (document.getElementById(t3));
          return t3;
        })(this.constructor.NAME).toString();
        return e2.setAttribute("id", i2), this._isAnimated() && e2.classList.add(ts), e2;
      }
      setContent(t2) {
        this._newContent = t2, this._isShown() && (this._disposePopper(), this.show());
      }
      _getTemplateFactory(t2) {
        return this._templateFactory ? this._templateFactory.changeContent(t2) : this._templateFactory = new Jn({ ...this._config, content: t2, extraClass: this._resolvePossibleFunction(this._config.customClass) }), this._templateFactory;
      }
      _getContentForTemplate() {
        return { ".tooltip-inner": this._getTitle() };
      }
      _getTitle() {
        return this._resolvePossibleFunction(this._config.title) || this._element.getAttribute("data-bs-original-title");
      }
      _initializeOnDelegatedTarget(t2) {
        return this.constructor.getOrCreateInstance(t2.delegateTarget, this._getDelegateConfig());
      }
      _isAnimated() {
        return this._config.animation || this.tip && this.tip.classList.contains(ts);
      }
      _isShown() {
        return this.tip && this.tip.classList.contains(es);
      }
      _createPopper(t2) {
        const e2 = g(this._config.placement, [this, t2, this._element]), i2 = rs[e2.toUpperCase()];
        return bi(this._element, t2, this._getPopperConfig(i2));
      }
      _getOffset() {
        const { offset: t2 } = this._config;
        return "string" == typeof t2 ? t2.split(",").map((t3) => Number.parseInt(t3, 10)) : "function" == typeof t2 ? (e2) => t2(e2, this._element) : t2;
      }
      _resolvePossibleFunction(t2) {
        return g(t2, [this._element]);
      }
      _getPopperConfig(t2) {
        const e2 = { placement: t2, modifiers: [{ name: "flip", options: { fallbackPlacements: this._config.fallbackPlacements } }, { name: "offset", options: { offset: this._getOffset() } }, { name: "preventOverflow", options: { boundary: this._config.boundary } }, { name: "arrow", options: { element: `.${this.constructor.NAME}-arrow` } }, { name: "preSetPlacement", enabled: true, phase: "beforeMain", fn: (t3) => {
          this._getTipElement().setAttribute("data-popper-placement", t3.state.placement);
        } }] };
        return { ...e2, ...g(this._config.popperConfig, [e2]) };
      }
      _setListeners() {
        const t2 = this._config.trigger.split(" ");
        for (const e2 of t2)
          if ("click" === e2)
            N.on(this._element, this.constructor.eventName("click"), this._config.selector, (t3) => {
              this._initializeOnDelegatedTarget(t3).toggle();
            });
          else if ("manual" !== e2) {
            const t3 = e2 === ss ? this.constructor.eventName("mouseenter") : this.constructor.eventName("focusin"), i2 = e2 === ss ? this.constructor.eventName("mouseleave") : this.constructor.eventName("focusout");
            N.on(this._element, t3, this._config.selector, (t4) => {
              const e3 = this._initializeOnDelegatedTarget(t4);
              e3._activeTrigger["focusin" === t4.type ? os : ss] = true, e3._enter();
            }), N.on(this._element, i2, this._config.selector, (t4) => {
              const e3 = this._initializeOnDelegatedTarget(t4);
              e3._activeTrigger["focusout" === t4.type ? os : ss] = e3._element.contains(t4.relatedTarget), e3._leave();
            });
          }
        this._hideModalHandler = () => {
          this._element && this.hide();
        }, N.on(this._element.closest(is), ns, this._hideModalHandler);
      }
      _fixTitle() {
        const t2 = this._element.getAttribute("title");
        t2 && (this._element.getAttribute("aria-label") || this._element.textContent.trim() || this._element.setAttribute("aria-label", t2), this._element.setAttribute("data-bs-original-title", t2), this._element.removeAttribute("title"));
      }
      _enter() {
        this._isShown() || this._isHovered ? this._isHovered = true : (this._isHovered = true, this._setTimeout(() => {
          this._isHovered && this.show();
        }, this._config.delay.show));
      }
      _leave() {
        this._isWithActiveTrigger() || (this._isHovered = false, this._setTimeout(() => {
          this._isHovered || this.hide();
        }, this._config.delay.hide));
      }
      _setTimeout(t2, e2) {
        clearTimeout(this._timeout), this._timeout = setTimeout(t2, e2);
      }
      _isWithActiveTrigger() {
        return Object.values(this._activeTrigger).includes(true);
      }
      _getConfig(t2) {
        const e2 = F.getDataAttributes(this._element);
        for (const t3 of Object.keys(e2))
          Zn.has(t3) && delete e2[t3];
        return t2 = { ...e2, ..."object" == typeof t2 && t2 ? t2 : {} }, t2 = this._mergeConfigObj(t2), t2 = this._configAfterMerge(t2), this._typeCheckConfig(t2), t2;
      }
      _configAfterMerge(t2) {
        return t2.container = false === t2.container ? document.body : r(t2.container), "number" == typeof t2.delay && (t2.delay = { show: t2.delay, hide: t2.delay }), "number" == typeof t2.title && (t2.title = t2.title.toString()), "number" == typeof t2.content && (t2.content = t2.content.toString()), t2;
      }
      _getDelegateConfig() {
        const t2 = {};
        for (const [e2, i2] of Object.entries(this._config))
          this.constructor.Default[e2] !== i2 && (t2[e2] = i2);
        return t2.selector = false, t2.trigger = "manual", t2;
      }
      _disposePopper() {
        this._popper && (this._popper.destroy(), this._popper = null), this.tip && (this.tip.remove(), this.tip = null);
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = cs.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2])
              throw new TypeError(`No method named "${t2}"`);
            e2[t2]();
          }
        });
      }
    }
    m3(cs);
    const hs = { ...cs.Default, content: "", offset: [0, 8], placement: "right", template: '<div class="popover" role="tooltip"><div class="popover-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>', trigger: "click" }, ds = { ...cs.DefaultType, content: "(null|string|element|function)" };
    class us extends cs {
      static get Default() {
        return hs;
      }
      static get DefaultType() {
        return ds;
      }
      static get NAME() {
        return "popover";
      }
      _isWithContent() {
        return this._getTitle() || this._getContent();
      }
      _getContentForTemplate() {
        return { ".popover-header": this._getTitle(), ".popover-body": this._getContent() };
      }
      _getContent() {
        return this._resolvePossibleFunction(this._config.content);
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = us.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2])
              throw new TypeError(`No method named "${t2}"`);
            e2[t2]();
          }
        });
      }
    }
    m3(us);
    const fs = ".bs.scrollspy", ps = `activate${fs}`, ms = `click${fs}`, gs = `load${fs}.data-api`, _s = "active", bs = "[href]", vs = ".nav-link", ys = `${vs}, .nav-item > ${vs}, .list-group-item`, ws = { offset: null, rootMargin: "0px 0px -25%", smoothScroll: false, target: null, threshold: [0.1, 0.5, 1] }, As = { offset: "(number|null)", rootMargin: "string", smoothScroll: "boolean", target: "element", threshold: "array" };
    class Es extends W {
      constructor(t2, e2) {
        super(t2, e2), this._targetLinks = /* @__PURE__ */ new Map(), this._observableSections = /* @__PURE__ */ new Map(), this._rootElement = "visible" === getComputedStyle(this._element).overflowY ? null : this._element, this._activeTarget = null, this._observer = null, this._previousScrollData = { visibleEntryTop: 0, parentScrollTop: 0 }, this.refresh();
      }
      static get Default() {
        return ws;
      }
      static get DefaultType() {
        return As;
      }
      static get NAME() {
        return "scrollspy";
      }
      refresh() {
        this._initializeTargetsAndObservables(), this._maybeEnableSmoothScroll(), this._observer ? this._observer.disconnect() : this._observer = this._getNewObserver();
        for (const t2 of this._observableSections.values())
          this._observer.observe(t2);
      }
      dispose() {
        this._observer.disconnect(), super.dispose();
      }
      _configAfterMerge(t2) {
        return t2.target = r(t2.target) || document.body, t2.rootMargin = t2.offset ? `${t2.offset}px 0px -30%` : t2.rootMargin, "string" == typeof t2.threshold && (t2.threshold = t2.threshold.split(",").map((t3) => Number.parseFloat(t3))), t2;
      }
      _maybeEnableSmoothScroll() {
        this._config.smoothScroll && (N.off(this._config.target, ms), N.on(this._config.target, ms, bs, (t2) => {
          const e2 = this._observableSections.get(t2.target.hash);
          if (e2) {
            t2.preventDefault();
            const i2 = this._rootElement || window, n2 = e2.offsetTop - this._element.offsetTop;
            if (i2.scrollTo)
              return void i2.scrollTo({ top: n2, behavior: "smooth" });
            i2.scrollTop = n2;
          }
        }));
      }
      _getNewObserver() {
        const t2 = { root: this._rootElement, threshold: this._config.threshold, rootMargin: this._config.rootMargin };
        return new IntersectionObserver((t3) => this._observerCallback(t3), t2);
      }
      _observerCallback(t2) {
        const e2 = (t3) => this._targetLinks.get(`#${t3.target.id}`), i2 = (t3) => {
          this._previousScrollData.visibleEntryTop = t3.target.offsetTop, this._process(e2(t3));
        }, n2 = (this._rootElement || document.documentElement).scrollTop, s2 = n2 >= this._previousScrollData.parentScrollTop;
        this._previousScrollData.parentScrollTop = n2;
        for (const o2 of t2) {
          if (!o2.isIntersecting) {
            this._activeTarget = null, this._clearActiveClass(e2(o2));
            continue;
          }
          const t3 = o2.target.offsetTop >= this._previousScrollData.visibleEntryTop;
          if (s2 && t3) {
            if (i2(o2), !n2)
              return;
          } else
            s2 || t3 || i2(o2);
        }
      }
      _initializeTargetsAndObservables() {
        this._targetLinks = /* @__PURE__ */ new Map(), this._observableSections = /* @__PURE__ */ new Map();
        const t2 = z.find(bs, this._config.target);
        for (const e2 of t2) {
          if (!e2.hash || l(e2))
            continue;
          const t3 = z.findOne(decodeURI(e2.hash), this._element);
          a(t3) && (this._targetLinks.set(decodeURI(e2.hash), e2), this._observableSections.set(e2.hash, t3));
        }
      }
      _process(t2) {
        this._activeTarget !== t2 && (this._clearActiveClass(this._config.target), this._activeTarget = t2, t2.classList.add(_s), this._activateParents(t2), N.trigger(this._element, ps, { relatedTarget: t2 }));
      }
      _activateParents(t2) {
        if (t2.classList.contains("dropdown-item"))
          z.findOne(".dropdown-toggle", t2.closest(".dropdown")).classList.add(_s);
        else
          for (const e2 of z.parents(t2, ".nav, .list-group"))
            for (const t3 of z.prev(e2, ys))
              t3.classList.add(_s);
      }
      _clearActiveClass(t2) {
        t2.classList.remove(_s);
        const e2 = z.find(`${bs}.${_s}`, t2);
        for (const t3 of e2)
          t3.classList.remove(_s);
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = Es.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2] || t2.startsWith("_") || "constructor" === t2)
              throw new TypeError(`No method named "${t2}"`);
            e2[t2]();
          }
        });
      }
    }
    N.on(window, gs, () => {
      for (const t2 of z.find('[data-bs-spy="scroll"]'))
        Es.getOrCreateInstance(t2);
    }), m3(Es);
    const Ts = ".bs.tab", Cs = `hide${Ts}`, Os = `hidden${Ts}`, xs = `show${Ts}`, ks = `shown${Ts}`, Ls = `click${Ts}`, Ss = `keydown${Ts}`, Ds = `load${Ts}`, $s = "ArrowLeft", Is = "ArrowRight", Ns = "ArrowUp", Ps = "ArrowDown", js = "Home", Ms = "End", Fs = "active", Hs = "fade", Ws = "show", Bs = ".dropdown-toggle", zs = `:not(${Bs})`, Rs = '[data-bs-toggle="tab"], [data-bs-toggle="pill"], [data-bs-toggle="list"]', qs = `.nav-link${zs}, .list-group-item${zs}, [role="tab"]${zs}, ${Rs}`, Vs = `.${Fs}[data-bs-toggle="tab"], .${Fs}[data-bs-toggle="pill"], .${Fs}[data-bs-toggle="list"]`;
    class Ks extends W {
      constructor(t2) {
        super(t2), this._parent = this._element.closest('.list-group, .nav, [role="tablist"]'), this._parent && (this._setInitialAttributes(this._parent, this._getChildren()), N.on(this._element, Ss, (t3) => this._keydown(t3)));
      }
      static get NAME() {
        return "tab";
      }
      show() {
        const t2 = this._element;
        if (this._elemIsActive(t2))
          return;
        const e2 = this._getActiveElem(), i2 = e2 ? N.trigger(e2, Cs, { relatedTarget: t2 }) : null;
        N.trigger(t2, xs, { relatedTarget: e2 }).defaultPrevented || i2 && i2.defaultPrevented || (this._deactivate(e2, t2), this._activate(t2, e2));
      }
      _activate(t2, e2) {
        t2 && (t2.classList.add(Fs), this._activate(z.getElementFromSelector(t2)), this._queueCallback(() => {
          "tab" === t2.getAttribute("role") ? (t2.removeAttribute("tabindex"), t2.setAttribute("aria-selected", true), this._toggleDropDown(t2, true), N.trigger(t2, ks, { relatedTarget: e2 })) : t2.classList.add(Ws);
        }, t2, t2.classList.contains(Hs)));
      }
      _deactivate(t2, e2) {
        t2 && (t2.classList.remove(Fs), t2.blur(), this._deactivate(z.getElementFromSelector(t2)), this._queueCallback(() => {
          "tab" === t2.getAttribute("role") ? (t2.setAttribute("aria-selected", false), t2.setAttribute("tabindex", "-1"), this._toggleDropDown(t2, false), N.trigger(t2, Os, { relatedTarget: e2 })) : t2.classList.remove(Ws);
        }, t2, t2.classList.contains(Hs)));
      }
      _keydown(t2) {
        if (![$s, Is, Ns, Ps, js, Ms].includes(t2.key))
          return;
        t2.stopPropagation(), t2.preventDefault();
        const e2 = this._getChildren().filter((t3) => !l(t3));
        let i2;
        if ([js, Ms].includes(t2.key))
          i2 = e2[t2.key === js ? 0 : e2.length - 1];
        else {
          const n2 = [Is, Ps].includes(t2.key);
          i2 = b(e2, t2.target, n2, true);
        }
        i2 && (i2.focus({ preventScroll: true }), Ks.getOrCreateInstance(i2).show());
      }
      _getChildren() {
        return z.find(qs, this._parent);
      }
      _getActiveElem() {
        return this._getChildren().find((t2) => this._elemIsActive(t2)) || null;
      }
      _setInitialAttributes(t2, e2) {
        this._setAttributeIfNotExists(t2, "role", "tablist");
        for (const t3 of e2)
          this._setInitialAttributesOnChild(t3);
      }
      _setInitialAttributesOnChild(t2) {
        t2 = this._getInnerElement(t2);
        const e2 = this._elemIsActive(t2), i2 = this._getOuterElement(t2);
        t2.setAttribute("aria-selected", e2), i2 !== t2 && this._setAttributeIfNotExists(i2, "role", "presentation"), e2 || t2.setAttribute("tabindex", "-1"), this._setAttributeIfNotExists(t2, "role", "tab"), this._setInitialAttributesOnTargetPanel(t2);
      }
      _setInitialAttributesOnTargetPanel(t2) {
        const e2 = z.getElementFromSelector(t2);
        e2 && (this._setAttributeIfNotExists(e2, "role", "tabpanel"), t2.id && this._setAttributeIfNotExists(e2, "aria-labelledby", `${t2.id}`));
      }
      _toggleDropDown(t2, e2) {
        const i2 = this._getOuterElement(t2);
        if (!i2.classList.contains("dropdown"))
          return;
        const n2 = (t3, n3) => {
          const s2 = z.findOne(t3, i2);
          s2 && s2.classList.toggle(n3, e2);
        };
        n2(Bs, Fs), n2(".dropdown-menu", Ws), i2.setAttribute("aria-expanded", e2);
      }
      _setAttributeIfNotExists(t2, e2, i2) {
        t2.hasAttribute(e2) || t2.setAttribute(e2, i2);
      }
      _elemIsActive(t2) {
        return t2.classList.contains(Fs);
      }
      _getInnerElement(t2) {
        return t2.matches(qs) ? t2 : z.findOne(qs, t2);
      }
      _getOuterElement(t2) {
        return t2.closest(".nav-item, .list-group-item") || t2;
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = Ks.getOrCreateInstance(this);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2] || t2.startsWith("_") || "constructor" === t2)
              throw new TypeError(`No method named "${t2}"`);
            e2[t2]();
          }
        });
      }
    }
    N.on(document, Ls, Rs, function(t2) {
      ["A", "AREA"].includes(this.tagName) && t2.preventDefault(), l(this) || Ks.getOrCreateInstance(this).show();
    }), N.on(window, Ds, () => {
      for (const t2 of z.find(Vs))
        Ks.getOrCreateInstance(t2);
    }), m3(Ks);
    const Qs = ".bs.toast", Xs = `mouseover${Qs}`, Ys = `mouseout${Qs}`, Us = `focusin${Qs}`, Gs = `focusout${Qs}`, Js = `hide${Qs}`, Zs = `hidden${Qs}`, to = `show${Qs}`, eo = `shown${Qs}`, io = "hide", no = "show", so = "showing", oo = { animation: "boolean", autohide: "boolean", delay: "number" }, ro = { animation: true, autohide: true, delay: 5e3 };
    class ao extends W {
      constructor(t2, e2) {
        super(t2, e2), this._timeout = null, this._hasMouseInteraction = false, this._hasKeyboardInteraction = false, this._setListeners();
      }
      static get Default() {
        return ro;
      }
      static get DefaultType() {
        return oo;
      }
      static get NAME() {
        return "toast";
      }
      show() {
        N.trigger(this._element, to).defaultPrevented || (this._clearTimeout(), this._config.animation && this._element.classList.add("fade"), this._element.classList.remove(io), d(this._element), this._element.classList.add(no, so), this._queueCallback(() => {
          this._element.classList.remove(so), N.trigger(this._element, eo), this._maybeScheduleHide();
        }, this._element, this._config.animation));
      }
      hide() {
        this.isShown() && (N.trigger(this._element, Js).defaultPrevented || (this._element.classList.add(so), this._queueCallback(() => {
          this._element.classList.add(io), this._element.classList.remove(so, no), N.trigger(this._element, Zs);
        }, this._element, this._config.animation)));
      }
      dispose() {
        this._clearTimeout(), this.isShown() && this._element.classList.remove(no), super.dispose();
      }
      isShown() {
        return this._element.classList.contains(no);
      }
      _maybeScheduleHide() {
        this._config.autohide && (this._hasMouseInteraction || this._hasKeyboardInteraction || (this._timeout = setTimeout(() => {
          this.hide();
        }, this._config.delay)));
      }
      _onInteraction(t2, e2) {
        switch (t2.type) {
          case "mouseover":
          case "mouseout":
            this._hasMouseInteraction = e2;
            break;
          case "focusin":
          case "focusout":
            this._hasKeyboardInteraction = e2;
        }
        if (e2)
          return void this._clearTimeout();
        const i2 = t2.relatedTarget;
        this._element === i2 || this._element.contains(i2) || this._maybeScheduleHide();
      }
      _setListeners() {
        N.on(this._element, Xs, (t2) => this._onInteraction(t2, true)), N.on(this._element, Ys, (t2) => this._onInteraction(t2, false)), N.on(this._element, Us, (t2) => this._onInteraction(t2, true)), N.on(this._element, Gs, (t2) => this._onInteraction(t2, false));
      }
      _clearTimeout() {
        clearTimeout(this._timeout), this._timeout = null;
      }
      static jQueryInterface(t2) {
        return this.each(function() {
          const e2 = ao.getOrCreateInstance(this, t2);
          if ("string" == typeof t2) {
            if (void 0 === e2[t2])
              throw new TypeError(`No method named "${t2}"`);
            e2[t2](this);
          }
        });
      }
    }
    return R(ao), m3(ao), { Alert: Q, Button: Y, Carousel: xt, Collapse: Bt, Dropdown: qi, Modal: On, Offcanvas: qn, Popover: us, ScrollSpy: Es, Tab: Ks, Toast: ao, Tooltip: cs };
  });
})(bootstrap_bundle_min);
var all_min = "";
var index = "";
const millisecondsInWeek = 6048e5;
const millisecondsInDay = 864e5;
const minutesInMonth = 43200;
const minutesInDay = 1440;
const constructFromSymbol = Symbol.for("constructDateFrom");
function constructFrom(date, value) {
  if (typeof date === "function")
    return date(value);
  if (date && typeof date === "object" && constructFromSymbol in date)
    return date[constructFromSymbol](value);
  if (date instanceof Date)
    return new date.constructor(value);
  return new Date(value);
}
function toDate(argument, context) {
  return constructFrom(context || argument, argument);
}
let defaultOptions = {};
function getDefaultOptions() {
  return defaultOptions;
}
function startOfWeek(date, options) {
  var _a, _b, _c, _d, _e, _f, _g, _h;
  const defaultOptions2 = getDefaultOptions();
  const weekStartsOn = (_h = (_g = (_d = (_c = options == null ? void 0 : options.weekStartsOn) != null ? _c : (_b = (_a = options == null ? void 0 : options.locale) == null ? void 0 : _a.options) == null ? void 0 : _b.weekStartsOn) != null ? _d : defaultOptions2.weekStartsOn) != null ? _g : (_f = (_e = defaultOptions2.locale) == null ? void 0 : _e.options) == null ? void 0 : _f.weekStartsOn) != null ? _h : 0;
  const _date = toDate(date, options == null ? void 0 : options.in);
  const day = _date.getDay();
  const diff = (day < weekStartsOn ? 7 : 0) + day - weekStartsOn;
  _date.setDate(_date.getDate() - diff);
  _date.setHours(0, 0, 0, 0);
  return _date;
}
function startOfISOWeek(date, options) {
  return startOfWeek(date, { ...options, weekStartsOn: 1 });
}
function getISOWeekYear(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  const year = _date.getFullYear();
  const fourthOfJanuaryOfNextYear = constructFrom(_date, 0);
  fourthOfJanuaryOfNextYear.setFullYear(year + 1, 0, 4);
  fourthOfJanuaryOfNextYear.setHours(0, 0, 0, 0);
  const startOfNextYear = startOfISOWeek(fourthOfJanuaryOfNextYear);
  const fourthOfJanuaryOfThisYear = constructFrom(_date, 0);
  fourthOfJanuaryOfThisYear.setFullYear(year, 0, 4);
  fourthOfJanuaryOfThisYear.setHours(0, 0, 0, 0);
  const startOfThisYear = startOfISOWeek(fourthOfJanuaryOfThisYear);
  if (_date.getTime() >= startOfNextYear.getTime()) {
    return year + 1;
  } else if (_date.getTime() >= startOfThisYear.getTime()) {
    return year;
  } else {
    return year - 1;
  }
}
function getTimezoneOffsetInMilliseconds(date) {
  const _date = toDate(date);
  const utcDate = new Date(
    Date.UTC(
      _date.getFullYear(),
      _date.getMonth(),
      _date.getDate(),
      _date.getHours(),
      _date.getMinutes(),
      _date.getSeconds(),
      _date.getMilliseconds()
    )
  );
  utcDate.setUTCFullYear(_date.getFullYear());
  return +date - +utcDate;
}
function normalizeDates(context, ...dates) {
  const normalize = constructFrom.bind(
    null,
    context || dates.find((date) => typeof date === "object")
  );
  return dates.map(normalize);
}
function startOfDay(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  _date.setHours(0, 0, 0, 0);
  return _date;
}
function differenceInCalendarDays(laterDate, earlierDate, options) {
  const [laterDate_, earlierDate_] = normalizeDates(
    options == null ? void 0 : options.in,
    laterDate,
    earlierDate
  );
  const laterStartOfDay = startOfDay(laterDate_);
  const earlierStartOfDay = startOfDay(earlierDate_);
  const laterTimestamp = +laterStartOfDay - getTimezoneOffsetInMilliseconds(laterStartOfDay);
  const earlierTimestamp = +earlierStartOfDay - getTimezoneOffsetInMilliseconds(earlierStartOfDay);
  return Math.round((laterTimestamp - earlierTimestamp) / millisecondsInDay);
}
function startOfISOWeekYear(date, options) {
  const year = getISOWeekYear(date, options);
  const fourthOfJanuary = constructFrom((options == null ? void 0 : options.in) || date, 0);
  fourthOfJanuary.setFullYear(year, 0, 4);
  fourthOfJanuary.setHours(0, 0, 0, 0);
  return startOfISOWeek(fourthOfJanuary);
}
function compareAsc(dateLeft, dateRight) {
  const diff = +toDate(dateLeft) - +toDate(dateRight);
  if (diff < 0)
    return -1;
  else if (diff > 0)
    return 1;
  return diff;
}
function constructNow(date) {
  return constructFrom(date, Date.now());
}
function isDate(value) {
  return value instanceof Date || typeof value === "object" && Object.prototype.toString.call(value) === "[object Date]";
}
function isValid(date) {
  return !(!isDate(date) && typeof date !== "number" || isNaN(+toDate(date)));
}
function differenceInCalendarMonths(laterDate, earlierDate, options) {
  const [laterDate_, earlierDate_] = normalizeDates(
    options == null ? void 0 : options.in,
    laterDate,
    earlierDate
  );
  const yearsDiff = laterDate_.getFullYear() - earlierDate_.getFullYear();
  const monthsDiff = laterDate_.getMonth() - earlierDate_.getMonth();
  return yearsDiff * 12 + monthsDiff;
}
function getRoundingMethod(method) {
  return (number) => {
    const round = method ? Math[method] : Math.trunc;
    const result = round(number);
    return result === 0 ? 0 : result;
  };
}
function differenceInMilliseconds(laterDate, earlierDate) {
  return +toDate(laterDate) - +toDate(earlierDate);
}
function endOfDay(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  _date.setHours(23, 59, 59, 999);
  return _date;
}
function endOfMonth(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  const month = _date.getMonth();
  _date.setFullYear(_date.getFullYear(), month + 1, 0);
  _date.setHours(23, 59, 59, 999);
  return _date;
}
function isLastDayOfMonth(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  return +endOfDay(_date, options) === +endOfMonth(_date, options);
}
function differenceInMonths(laterDate, earlierDate, options) {
  const [laterDate_, workingLaterDate, earlierDate_] = normalizeDates(
    options == null ? void 0 : options.in,
    laterDate,
    laterDate,
    earlierDate
  );
  const sign = compareAsc(workingLaterDate, earlierDate_);
  const difference = Math.abs(
    differenceInCalendarMonths(workingLaterDate, earlierDate_)
  );
  if (difference < 1)
    return 0;
  if (workingLaterDate.getMonth() === 1 && workingLaterDate.getDate() > 27)
    workingLaterDate.setDate(30);
  workingLaterDate.setMonth(workingLaterDate.getMonth() - sign * difference);
  let isLastMonthNotFull = compareAsc(workingLaterDate, earlierDate_) === -sign;
  if (isLastDayOfMonth(laterDate_) && difference === 1 && compareAsc(laterDate_, earlierDate_) === 1) {
    isLastMonthNotFull = false;
  }
  const result = sign * (difference - +isLastMonthNotFull);
  return result === 0 ? 0 : result;
}
function differenceInSeconds(laterDate, earlierDate, options) {
  const diff = differenceInMilliseconds(laterDate, earlierDate) / 1e3;
  return getRoundingMethod(options == null ? void 0 : options.roundingMethod)(diff);
}
function startOfYear(date, options) {
  const date_ = toDate(date, options == null ? void 0 : options.in);
  date_.setFullYear(date_.getFullYear(), 0, 1);
  date_.setHours(0, 0, 0, 0);
  return date_;
}
const formatDistanceLocale = {
  lessThanXSeconds: {
    one: "less than a second",
    other: "less than {{count}} seconds"
  },
  xSeconds: {
    one: "1 second",
    other: "{{count}} seconds"
  },
  halfAMinute: "half a minute",
  lessThanXMinutes: {
    one: "less than a minute",
    other: "less than {{count}} minutes"
  },
  xMinutes: {
    one: "1 minute",
    other: "{{count}} minutes"
  },
  aboutXHours: {
    one: "about 1 hour",
    other: "about {{count}} hours"
  },
  xHours: {
    one: "1 hour",
    other: "{{count}} hours"
  },
  xDays: {
    one: "1 day",
    other: "{{count}} days"
  },
  aboutXWeeks: {
    one: "about 1 week",
    other: "about {{count}} weeks"
  },
  xWeeks: {
    one: "1 week",
    other: "{{count}} weeks"
  },
  aboutXMonths: {
    one: "about 1 month",
    other: "about {{count}} months"
  },
  xMonths: {
    one: "1 month",
    other: "{{count}} months"
  },
  aboutXYears: {
    one: "about 1 year",
    other: "about {{count}} years"
  },
  xYears: {
    one: "1 year",
    other: "{{count}} years"
  },
  overXYears: {
    one: "over 1 year",
    other: "over {{count}} years"
  },
  almostXYears: {
    one: "almost 1 year",
    other: "almost {{count}} years"
  }
};
const formatDistance$1 = (token, count, options) => {
  let result;
  const tokenValue = formatDistanceLocale[token];
  if (typeof tokenValue === "string") {
    result = tokenValue;
  } else if (count === 1) {
    result = tokenValue.one;
  } else {
    result = tokenValue.other.replace("{{count}}", count.toString());
  }
  if (options == null ? void 0 : options.addSuffix) {
    if (options.comparison && options.comparison > 0) {
      return "in " + result;
    } else {
      return result + " ago";
    }
  }
  return result;
};
function buildFormatLongFn(args) {
  return (options = {}) => {
    const width = options.width ? String(options.width) : args.defaultWidth;
    const format2 = args.formats[width] || args.formats[args.defaultWidth];
    return format2;
  };
}
const dateFormats = {
  full: "EEEE, MMMM do, y",
  long: "MMMM do, y",
  medium: "MMM d, y",
  short: "MM/dd/yyyy"
};
const timeFormats = {
  full: "h:mm:ss a zzzz",
  long: "h:mm:ss a z",
  medium: "h:mm:ss a",
  short: "h:mm a"
};
const dateTimeFormats = {
  full: "{{date}} 'at' {{time}}",
  long: "{{date}} 'at' {{time}}",
  medium: "{{date}}, {{time}}",
  short: "{{date}}, {{time}}"
};
const formatLong = {
  date: buildFormatLongFn({
    formats: dateFormats,
    defaultWidth: "full"
  }),
  time: buildFormatLongFn({
    formats: timeFormats,
    defaultWidth: "full"
  }),
  dateTime: buildFormatLongFn({
    formats: dateTimeFormats,
    defaultWidth: "full"
  })
};
const formatRelativeLocale = {
  lastWeek: "'last' eeee 'at' p",
  yesterday: "'yesterday at' p",
  today: "'today at' p",
  tomorrow: "'tomorrow at' p",
  nextWeek: "eeee 'at' p",
  other: "P"
};
const formatRelative = (token, _date, _baseDate, _options) => formatRelativeLocale[token];
function buildLocalizeFn(args) {
  return (value, options) => {
    const context = (options == null ? void 0 : options.context) ? String(options.context) : "standalone";
    let valuesArray;
    if (context === "formatting" && args.formattingValues) {
      const defaultWidth = args.defaultFormattingWidth || args.defaultWidth;
      const width = (options == null ? void 0 : options.width) ? String(options.width) : defaultWidth;
      valuesArray = args.formattingValues[width] || args.formattingValues[defaultWidth];
    } else {
      const defaultWidth = args.defaultWidth;
      const width = (options == null ? void 0 : options.width) ? String(options.width) : args.defaultWidth;
      valuesArray = args.values[width] || args.values[defaultWidth];
    }
    const index2 = args.argumentCallback ? args.argumentCallback(value) : value;
    return valuesArray[index2];
  };
}
const eraValues = {
  narrow: ["B", "A"],
  abbreviated: ["BC", "AD"],
  wide: ["Before Christ", "Anno Domini"]
};
const quarterValues = {
  narrow: ["1", "2", "3", "4"],
  abbreviated: ["Q1", "Q2", "Q3", "Q4"],
  wide: ["1st quarter", "2nd quarter", "3rd quarter", "4th quarter"]
};
const monthValues = {
  narrow: ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"],
  abbreviated: [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec"
  ],
  wide: [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
  ]
};
const dayValues = {
  narrow: ["S", "M", "T", "W", "T", "F", "S"],
  short: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
  abbreviated: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  wide: [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
  ]
};
const dayPeriodValues = {
  narrow: {
    am: "a",
    pm: "p",
    midnight: "mi",
    noon: "n",
    morning: "morning",
    afternoon: "afternoon",
    evening: "evening",
    night: "night"
  },
  abbreviated: {
    am: "AM",
    pm: "PM",
    midnight: "midnight",
    noon: "noon",
    morning: "morning",
    afternoon: "afternoon",
    evening: "evening",
    night: "night"
  },
  wide: {
    am: "a.m.",
    pm: "p.m.",
    midnight: "midnight",
    noon: "noon",
    morning: "morning",
    afternoon: "afternoon",
    evening: "evening",
    night: "night"
  }
};
const formattingDayPeriodValues = {
  narrow: {
    am: "a",
    pm: "p",
    midnight: "mi",
    noon: "n",
    morning: "in the morning",
    afternoon: "in the afternoon",
    evening: "in the evening",
    night: "at night"
  },
  abbreviated: {
    am: "AM",
    pm: "PM",
    midnight: "midnight",
    noon: "noon",
    morning: "in the morning",
    afternoon: "in the afternoon",
    evening: "in the evening",
    night: "at night"
  },
  wide: {
    am: "a.m.",
    pm: "p.m.",
    midnight: "midnight",
    noon: "noon",
    morning: "in the morning",
    afternoon: "in the afternoon",
    evening: "in the evening",
    night: "at night"
  }
};
const ordinalNumber = (dirtyNumber, _options) => {
  const number = Number(dirtyNumber);
  const rem100 = number % 100;
  if (rem100 > 20 || rem100 < 10) {
    switch (rem100 % 10) {
      case 1:
        return number + "st";
      case 2:
        return number + "nd";
      case 3:
        return number + "rd";
    }
  }
  return number + "th";
};
const localize = {
  ordinalNumber,
  era: buildLocalizeFn({
    values: eraValues,
    defaultWidth: "wide"
  }),
  quarter: buildLocalizeFn({
    values: quarterValues,
    defaultWidth: "wide",
    argumentCallback: (quarter) => quarter - 1
  }),
  month: buildLocalizeFn({
    values: monthValues,
    defaultWidth: "wide"
  }),
  day: buildLocalizeFn({
    values: dayValues,
    defaultWidth: "wide"
  }),
  dayPeriod: buildLocalizeFn({
    values: dayPeriodValues,
    defaultWidth: "wide",
    formattingValues: formattingDayPeriodValues,
    defaultFormattingWidth: "wide"
  })
};
function buildMatchFn(args) {
  return (string, options = {}) => {
    const width = options.width;
    const matchPattern = width && args.matchPatterns[width] || args.matchPatterns[args.defaultMatchWidth];
    const matchResult = string.match(matchPattern);
    if (!matchResult) {
      return null;
    }
    const matchedString = matchResult[0];
    const parsePatterns = width && args.parsePatterns[width] || args.parsePatterns[args.defaultParseWidth];
    const key = Array.isArray(parsePatterns) ? findIndex(parsePatterns, (pattern) => pattern.test(matchedString)) : findKey(parsePatterns, (pattern) => pattern.test(matchedString));
    let value;
    value = args.valueCallback ? args.valueCallback(key) : key;
    value = options.valueCallback ? options.valueCallback(value) : value;
    const rest = string.slice(matchedString.length);
    return { value, rest };
  };
}
function findKey(object, predicate) {
  for (const key in object) {
    if (Object.prototype.hasOwnProperty.call(object, key) && predicate(object[key])) {
      return key;
    }
  }
  return void 0;
}
function findIndex(array, predicate) {
  for (let key = 0; key < array.length; key++) {
    if (predicate(array[key])) {
      return key;
    }
  }
  return void 0;
}
function buildMatchPatternFn(args) {
  return (string, options = {}) => {
    const matchResult = string.match(args.matchPattern);
    if (!matchResult)
      return null;
    const matchedString = matchResult[0];
    const parseResult = string.match(args.parsePattern);
    if (!parseResult)
      return null;
    let value = args.valueCallback ? args.valueCallback(parseResult[0]) : parseResult[0];
    value = options.valueCallback ? options.valueCallback(value) : value;
    const rest = string.slice(matchedString.length);
    return { value, rest };
  };
}
const matchOrdinalNumberPattern = /^(\d+)(th|st|nd|rd)?/i;
const parseOrdinalNumberPattern = /\d+/i;
const matchEraPatterns = {
  narrow: /^(b|a)/i,
  abbreviated: /^(b\.?\s?c\.?|b\.?\s?c\.?\s?e\.?|a\.?\s?d\.?|c\.?\s?e\.?)/i,
  wide: /^(before christ|before common era|anno domini|common era)/i
};
const parseEraPatterns = {
  any: [/^b/i, /^(a|c)/i]
};
const matchQuarterPatterns = {
  narrow: /^[1234]/i,
  abbreviated: /^q[1234]/i,
  wide: /^[1234](th|st|nd|rd)? quarter/i
};
const parseQuarterPatterns = {
  any: [/1/i, /2/i, /3/i, /4/i]
};
const matchMonthPatterns = {
  narrow: /^[jfmasond]/i,
  abbreviated: /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i,
  wide: /^(january|february|march|april|may|june|july|august|september|october|november|december)/i
};
const parseMonthPatterns = {
  narrow: [
    /^j/i,
    /^f/i,
    /^m/i,
    /^a/i,
    /^m/i,
    /^j/i,
    /^j/i,
    /^a/i,
    /^s/i,
    /^o/i,
    /^n/i,
    /^d/i
  ],
  any: [
    /^ja/i,
    /^f/i,
    /^mar/i,
    /^ap/i,
    /^may/i,
    /^jun/i,
    /^jul/i,
    /^au/i,
    /^s/i,
    /^o/i,
    /^n/i,
    /^d/i
  ]
};
const matchDayPatterns = {
  narrow: /^[smtwf]/i,
  short: /^(su|mo|tu|we|th|fr|sa)/i,
  abbreviated: /^(sun|mon|tue|wed|thu|fri|sat)/i,
  wide: /^(sunday|monday|tuesday|wednesday|thursday|friday|saturday)/i
};
const parseDayPatterns = {
  narrow: [/^s/i, /^m/i, /^t/i, /^w/i, /^t/i, /^f/i, /^s/i],
  any: [/^su/i, /^m/i, /^tu/i, /^w/i, /^th/i, /^f/i, /^sa/i]
};
const matchDayPeriodPatterns = {
  narrow: /^(a|p|mi|n|(in the|at) (morning|afternoon|evening|night))/i,
  any: /^([ap]\.?\s?m\.?|midnight|noon|(in the|at) (morning|afternoon|evening|night))/i
};
const parseDayPeriodPatterns = {
  any: {
    am: /^a/i,
    pm: /^p/i,
    midnight: /^mi/i,
    noon: /^no/i,
    morning: /morning/i,
    afternoon: /afternoon/i,
    evening: /evening/i,
    night: /night/i
  }
};
const match = {
  ordinalNumber: buildMatchPatternFn({
    matchPattern: matchOrdinalNumberPattern,
    parsePattern: parseOrdinalNumberPattern,
    valueCallback: (value) => parseInt(value, 10)
  }),
  era: buildMatchFn({
    matchPatterns: matchEraPatterns,
    defaultMatchWidth: "wide",
    parsePatterns: parseEraPatterns,
    defaultParseWidth: "any"
  }),
  quarter: buildMatchFn({
    matchPatterns: matchQuarterPatterns,
    defaultMatchWidth: "wide",
    parsePatterns: parseQuarterPatterns,
    defaultParseWidth: "any",
    valueCallback: (index2) => index2 + 1
  }),
  month: buildMatchFn({
    matchPatterns: matchMonthPatterns,
    defaultMatchWidth: "wide",
    parsePatterns: parseMonthPatterns,
    defaultParseWidth: "any"
  }),
  day: buildMatchFn({
    matchPatterns: matchDayPatterns,
    defaultMatchWidth: "wide",
    parsePatterns: parseDayPatterns,
    defaultParseWidth: "any"
  }),
  dayPeriod: buildMatchFn({
    matchPatterns: matchDayPeriodPatterns,
    defaultMatchWidth: "any",
    parsePatterns: parseDayPeriodPatterns,
    defaultParseWidth: "any"
  })
};
const enUS = {
  code: "en-US",
  formatDistance: formatDistance$1,
  formatLong,
  formatRelative,
  localize,
  match,
  options: {
    weekStartsOn: 0,
    firstWeekContainsDate: 1
  }
};
function getDayOfYear(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  const diff = differenceInCalendarDays(_date, startOfYear(_date));
  const dayOfYear = diff + 1;
  return dayOfYear;
}
function getISOWeek(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  const diff = +startOfISOWeek(_date) - +startOfISOWeekYear(_date);
  return Math.round(diff / millisecondsInWeek) + 1;
}
function getWeekYear(date, options) {
  var _a, _b, _c, _d, _e, _f, _g, _h;
  const _date = toDate(date, options == null ? void 0 : options.in);
  const year = _date.getFullYear();
  const defaultOptions2 = getDefaultOptions();
  const firstWeekContainsDate = (_h = (_g = (_d = (_c = options == null ? void 0 : options.firstWeekContainsDate) != null ? _c : (_b = (_a = options == null ? void 0 : options.locale) == null ? void 0 : _a.options) == null ? void 0 : _b.firstWeekContainsDate) != null ? _d : defaultOptions2.firstWeekContainsDate) != null ? _g : (_f = (_e = defaultOptions2.locale) == null ? void 0 : _e.options) == null ? void 0 : _f.firstWeekContainsDate) != null ? _h : 1;
  const firstWeekOfNextYear = constructFrom((options == null ? void 0 : options.in) || date, 0);
  firstWeekOfNextYear.setFullYear(year + 1, 0, firstWeekContainsDate);
  firstWeekOfNextYear.setHours(0, 0, 0, 0);
  const startOfNextYear = startOfWeek(firstWeekOfNextYear, options);
  const firstWeekOfThisYear = constructFrom((options == null ? void 0 : options.in) || date, 0);
  firstWeekOfThisYear.setFullYear(year, 0, firstWeekContainsDate);
  firstWeekOfThisYear.setHours(0, 0, 0, 0);
  const startOfThisYear = startOfWeek(firstWeekOfThisYear, options);
  if (+_date >= +startOfNextYear) {
    return year + 1;
  } else if (+_date >= +startOfThisYear) {
    return year;
  } else {
    return year - 1;
  }
}
function startOfWeekYear(date, options) {
  var _a, _b, _c, _d, _e, _f, _g, _h;
  const defaultOptions2 = getDefaultOptions();
  const firstWeekContainsDate = (_h = (_g = (_d = (_c = options == null ? void 0 : options.firstWeekContainsDate) != null ? _c : (_b = (_a = options == null ? void 0 : options.locale) == null ? void 0 : _a.options) == null ? void 0 : _b.firstWeekContainsDate) != null ? _d : defaultOptions2.firstWeekContainsDate) != null ? _g : (_f = (_e = defaultOptions2.locale) == null ? void 0 : _e.options) == null ? void 0 : _f.firstWeekContainsDate) != null ? _h : 1;
  const year = getWeekYear(date, options);
  const firstWeek = constructFrom((options == null ? void 0 : options.in) || date, 0);
  firstWeek.setFullYear(year, 0, firstWeekContainsDate);
  firstWeek.setHours(0, 0, 0, 0);
  const _date = startOfWeek(firstWeek, options);
  return _date;
}
function getWeek(date, options) {
  const _date = toDate(date, options == null ? void 0 : options.in);
  const diff = +startOfWeek(_date, options) - +startOfWeekYear(_date, options);
  return Math.round(diff / millisecondsInWeek) + 1;
}
function addLeadingZeros(number, targetLength) {
  const sign = number < 0 ? "-" : "";
  const output = Math.abs(number).toString().padStart(targetLength, "0");
  return sign + output;
}
const lightFormatters = {
  y(date, token) {
    const signedYear = date.getFullYear();
    const year = signedYear > 0 ? signedYear : 1 - signedYear;
    return addLeadingZeros(token === "yy" ? year % 100 : year, token.length);
  },
  M(date, token) {
    const month = date.getMonth();
    return token === "M" ? String(month + 1) : addLeadingZeros(month + 1, 2);
  },
  d(date, token) {
    return addLeadingZeros(date.getDate(), token.length);
  },
  a(date, token) {
    const dayPeriodEnumValue = date.getHours() / 12 >= 1 ? "pm" : "am";
    switch (token) {
      case "a":
      case "aa":
        return dayPeriodEnumValue.toUpperCase();
      case "aaa":
        return dayPeriodEnumValue;
      case "aaaaa":
        return dayPeriodEnumValue[0];
      case "aaaa":
      default:
        return dayPeriodEnumValue === "am" ? "a.m." : "p.m.";
    }
  },
  h(date, token) {
    return addLeadingZeros(date.getHours() % 12 || 12, token.length);
  },
  H(date, token) {
    return addLeadingZeros(date.getHours(), token.length);
  },
  m(date, token) {
    return addLeadingZeros(date.getMinutes(), token.length);
  },
  s(date, token) {
    return addLeadingZeros(date.getSeconds(), token.length);
  },
  S(date, token) {
    const numberOfDigits = token.length;
    const milliseconds = date.getMilliseconds();
    const fractionalSeconds = Math.trunc(
      milliseconds * Math.pow(10, numberOfDigits - 3)
    );
    return addLeadingZeros(fractionalSeconds, token.length);
  }
};
const dayPeriodEnum = {
  am: "am",
  pm: "pm",
  midnight: "midnight",
  noon: "noon",
  morning: "morning",
  afternoon: "afternoon",
  evening: "evening",
  night: "night"
};
const formatters = {
  G: function(date, token, localize2) {
    const era = date.getFullYear() > 0 ? 1 : 0;
    switch (token) {
      case "G":
      case "GG":
      case "GGG":
        return localize2.era(era, { width: "abbreviated" });
      case "GGGGG":
        return localize2.era(era, { width: "narrow" });
      case "GGGG":
      default:
        return localize2.era(era, { width: "wide" });
    }
  },
  y: function(date, token, localize2) {
    if (token === "yo") {
      const signedYear = date.getFullYear();
      const year = signedYear > 0 ? signedYear : 1 - signedYear;
      return localize2.ordinalNumber(year, { unit: "year" });
    }
    return lightFormatters.y(date, token);
  },
  Y: function(date, token, localize2, options) {
    const signedWeekYear = getWeekYear(date, options);
    const weekYear = signedWeekYear > 0 ? signedWeekYear : 1 - signedWeekYear;
    if (token === "YY") {
      const twoDigitYear = weekYear % 100;
      return addLeadingZeros(twoDigitYear, 2);
    }
    if (token === "Yo") {
      return localize2.ordinalNumber(weekYear, { unit: "year" });
    }
    return addLeadingZeros(weekYear, token.length);
  },
  R: function(date, token) {
    const isoWeekYear = getISOWeekYear(date);
    return addLeadingZeros(isoWeekYear, token.length);
  },
  u: function(date, token) {
    const year = date.getFullYear();
    return addLeadingZeros(year, token.length);
  },
  Q: function(date, token, localize2) {
    const quarter = Math.ceil((date.getMonth() + 1) / 3);
    switch (token) {
      case "Q":
        return String(quarter);
      case "QQ":
        return addLeadingZeros(quarter, 2);
      case "Qo":
        return localize2.ordinalNumber(quarter, { unit: "quarter" });
      case "QQQ":
        return localize2.quarter(quarter, {
          width: "abbreviated",
          context: "formatting"
        });
      case "QQQQQ":
        return localize2.quarter(quarter, {
          width: "narrow",
          context: "formatting"
        });
      case "QQQQ":
      default:
        return localize2.quarter(quarter, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  q: function(date, token, localize2) {
    const quarter = Math.ceil((date.getMonth() + 1) / 3);
    switch (token) {
      case "q":
        return String(quarter);
      case "qq":
        return addLeadingZeros(quarter, 2);
      case "qo":
        return localize2.ordinalNumber(quarter, { unit: "quarter" });
      case "qqq":
        return localize2.quarter(quarter, {
          width: "abbreviated",
          context: "standalone"
        });
      case "qqqqq":
        return localize2.quarter(quarter, {
          width: "narrow",
          context: "standalone"
        });
      case "qqqq":
      default:
        return localize2.quarter(quarter, {
          width: "wide",
          context: "standalone"
        });
    }
  },
  M: function(date, token, localize2) {
    const month = date.getMonth();
    switch (token) {
      case "M":
      case "MM":
        return lightFormatters.M(date, token);
      case "Mo":
        return localize2.ordinalNumber(month + 1, { unit: "month" });
      case "MMM":
        return localize2.month(month, {
          width: "abbreviated",
          context: "formatting"
        });
      case "MMMMM":
        return localize2.month(month, {
          width: "narrow",
          context: "formatting"
        });
      case "MMMM":
      default:
        return localize2.month(month, { width: "wide", context: "formatting" });
    }
  },
  L: function(date, token, localize2) {
    const month = date.getMonth();
    switch (token) {
      case "L":
        return String(month + 1);
      case "LL":
        return addLeadingZeros(month + 1, 2);
      case "Lo":
        return localize2.ordinalNumber(month + 1, { unit: "month" });
      case "LLL":
        return localize2.month(month, {
          width: "abbreviated",
          context: "standalone"
        });
      case "LLLLL":
        return localize2.month(month, {
          width: "narrow",
          context: "standalone"
        });
      case "LLLL":
      default:
        return localize2.month(month, { width: "wide", context: "standalone" });
    }
  },
  w: function(date, token, localize2, options) {
    const week = getWeek(date, options);
    if (token === "wo") {
      return localize2.ordinalNumber(week, { unit: "week" });
    }
    return addLeadingZeros(week, token.length);
  },
  I: function(date, token, localize2) {
    const isoWeek = getISOWeek(date);
    if (token === "Io") {
      return localize2.ordinalNumber(isoWeek, { unit: "week" });
    }
    return addLeadingZeros(isoWeek, token.length);
  },
  d: function(date, token, localize2) {
    if (token === "do") {
      return localize2.ordinalNumber(date.getDate(), { unit: "date" });
    }
    return lightFormatters.d(date, token);
  },
  D: function(date, token, localize2) {
    const dayOfYear = getDayOfYear(date);
    if (token === "Do") {
      return localize2.ordinalNumber(dayOfYear, { unit: "dayOfYear" });
    }
    return addLeadingZeros(dayOfYear, token.length);
  },
  E: function(date, token, localize2) {
    const dayOfWeek = date.getDay();
    switch (token) {
      case "E":
      case "EE":
      case "EEE":
        return localize2.day(dayOfWeek, {
          width: "abbreviated",
          context: "formatting"
        });
      case "EEEEE":
        return localize2.day(dayOfWeek, {
          width: "narrow",
          context: "formatting"
        });
      case "EEEEEE":
        return localize2.day(dayOfWeek, {
          width: "short",
          context: "formatting"
        });
      case "EEEE":
      default:
        return localize2.day(dayOfWeek, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  e: function(date, token, localize2, options) {
    const dayOfWeek = date.getDay();
    const localDayOfWeek = (dayOfWeek - options.weekStartsOn + 8) % 7 || 7;
    switch (token) {
      case "e":
        return String(localDayOfWeek);
      case "ee":
        return addLeadingZeros(localDayOfWeek, 2);
      case "eo":
        return localize2.ordinalNumber(localDayOfWeek, { unit: "day" });
      case "eee":
        return localize2.day(dayOfWeek, {
          width: "abbreviated",
          context: "formatting"
        });
      case "eeeee":
        return localize2.day(dayOfWeek, {
          width: "narrow",
          context: "formatting"
        });
      case "eeeeee":
        return localize2.day(dayOfWeek, {
          width: "short",
          context: "formatting"
        });
      case "eeee":
      default:
        return localize2.day(dayOfWeek, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  c: function(date, token, localize2, options) {
    const dayOfWeek = date.getDay();
    const localDayOfWeek = (dayOfWeek - options.weekStartsOn + 8) % 7 || 7;
    switch (token) {
      case "c":
        return String(localDayOfWeek);
      case "cc":
        return addLeadingZeros(localDayOfWeek, token.length);
      case "co":
        return localize2.ordinalNumber(localDayOfWeek, { unit: "day" });
      case "ccc":
        return localize2.day(dayOfWeek, {
          width: "abbreviated",
          context: "standalone"
        });
      case "ccccc":
        return localize2.day(dayOfWeek, {
          width: "narrow",
          context: "standalone"
        });
      case "cccccc":
        return localize2.day(dayOfWeek, {
          width: "short",
          context: "standalone"
        });
      case "cccc":
      default:
        return localize2.day(dayOfWeek, {
          width: "wide",
          context: "standalone"
        });
    }
  },
  i: function(date, token, localize2) {
    const dayOfWeek = date.getDay();
    const isoDayOfWeek = dayOfWeek === 0 ? 7 : dayOfWeek;
    switch (token) {
      case "i":
        return String(isoDayOfWeek);
      case "ii":
        return addLeadingZeros(isoDayOfWeek, token.length);
      case "io":
        return localize2.ordinalNumber(isoDayOfWeek, { unit: "day" });
      case "iii":
        return localize2.day(dayOfWeek, {
          width: "abbreviated",
          context: "formatting"
        });
      case "iiiii":
        return localize2.day(dayOfWeek, {
          width: "narrow",
          context: "formatting"
        });
      case "iiiiii":
        return localize2.day(dayOfWeek, {
          width: "short",
          context: "formatting"
        });
      case "iiii":
      default:
        return localize2.day(dayOfWeek, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  a: function(date, token, localize2) {
    const hours = date.getHours();
    const dayPeriodEnumValue = hours / 12 >= 1 ? "pm" : "am";
    switch (token) {
      case "a":
      case "aa":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "abbreviated",
          context: "formatting"
        });
      case "aaa":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "abbreviated",
          context: "formatting"
        }).toLowerCase();
      case "aaaaa":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "narrow",
          context: "formatting"
        });
      case "aaaa":
      default:
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  b: function(date, token, localize2) {
    const hours = date.getHours();
    let dayPeriodEnumValue;
    if (hours === 12) {
      dayPeriodEnumValue = dayPeriodEnum.noon;
    } else if (hours === 0) {
      dayPeriodEnumValue = dayPeriodEnum.midnight;
    } else {
      dayPeriodEnumValue = hours / 12 >= 1 ? "pm" : "am";
    }
    switch (token) {
      case "b":
      case "bb":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "abbreviated",
          context: "formatting"
        });
      case "bbb":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "abbreviated",
          context: "formatting"
        }).toLowerCase();
      case "bbbbb":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "narrow",
          context: "formatting"
        });
      case "bbbb":
      default:
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  B: function(date, token, localize2) {
    const hours = date.getHours();
    let dayPeriodEnumValue;
    if (hours >= 17) {
      dayPeriodEnumValue = dayPeriodEnum.evening;
    } else if (hours >= 12) {
      dayPeriodEnumValue = dayPeriodEnum.afternoon;
    } else if (hours >= 4) {
      dayPeriodEnumValue = dayPeriodEnum.morning;
    } else {
      dayPeriodEnumValue = dayPeriodEnum.night;
    }
    switch (token) {
      case "B":
      case "BB":
      case "BBB":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "abbreviated",
          context: "formatting"
        });
      case "BBBBB":
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "narrow",
          context: "formatting"
        });
      case "BBBB":
      default:
        return localize2.dayPeriod(dayPeriodEnumValue, {
          width: "wide",
          context: "formatting"
        });
    }
  },
  h: function(date, token, localize2) {
    if (token === "ho") {
      let hours = date.getHours() % 12;
      if (hours === 0)
        hours = 12;
      return localize2.ordinalNumber(hours, { unit: "hour" });
    }
    return lightFormatters.h(date, token);
  },
  H: function(date, token, localize2) {
    if (token === "Ho") {
      return localize2.ordinalNumber(date.getHours(), { unit: "hour" });
    }
    return lightFormatters.H(date, token);
  },
  K: function(date, token, localize2) {
    const hours = date.getHours() % 12;
    if (token === "Ko") {
      return localize2.ordinalNumber(hours, { unit: "hour" });
    }
    return addLeadingZeros(hours, token.length);
  },
  k: function(date, token, localize2) {
    let hours = date.getHours();
    if (hours === 0)
      hours = 24;
    if (token === "ko") {
      return localize2.ordinalNumber(hours, { unit: "hour" });
    }
    return addLeadingZeros(hours, token.length);
  },
  m: function(date, token, localize2) {
    if (token === "mo") {
      return localize2.ordinalNumber(date.getMinutes(), { unit: "minute" });
    }
    return lightFormatters.m(date, token);
  },
  s: function(date, token, localize2) {
    if (token === "so") {
      return localize2.ordinalNumber(date.getSeconds(), { unit: "second" });
    }
    return lightFormatters.s(date, token);
  },
  S: function(date, token) {
    return lightFormatters.S(date, token);
  },
  X: function(date, token, _localize) {
    const timezoneOffset = date.getTimezoneOffset();
    if (timezoneOffset === 0) {
      return "Z";
    }
    switch (token) {
      case "X":
        return formatTimezoneWithOptionalMinutes(timezoneOffset);
      case "XXXX":
      case "XX":
        return formatTimezone(timezoneOffset);
      case "XXXXX":
      case "XXX":
      default:
        return formatTimezone(timezoneOffset, ":");
    }
  },
  x: function(date, token, _localize) {
    const timezoneOffset = date.getTimezoneOffset();
    switch (token) {
      case "x":
        return formatTimezoneWithOptionalMinutes(timezoneOffset);
      case "xxxx":
      case "xx":
        return formatTimezone(timezoneOffset);
      case "xxxxx":
      case "xxx":
      default:
        return formatTimezone(timezoneOffset, ":");
    }
  },
  O: function(date, token, _localize) {
    const timezoneOffset = date.getTimezoneOffset();
    switch (token) {
      case "O":
      case "OO":
      case "OOO":
        return "GMT" + formatTimezoneShort(timezoneOffset, ":");
      case "OOOO":
      default:
        return "GMT" + formatTimezone(timezoneOffset, ":");
    }
  },
  z: function(date, token, _localize) {
    const timezoneOffset = date.getTimezoneOffset();
    switch (token) {
      case "z":
      case "zz":
      case "zzz":
        return "GMT" + formatTimezoneShort(timezoneOffset, ":");
      case "zzzz":
      default:
        return "GMT" + formatTimezone(timezoneOffset, ":");
    }
  },
  t: function(date, token, _localize) {
    const timestamp = Math.trunc(+date / 1e3);
    return addLeadingZeros(timestamp, token.length);
  },
  T: function(date, token, _localize) {
    return addLeadingZeros(+date, token.length);
  }
};
function formatTimezoneShort(offset, delimiter = "") {
  const sign = offset > 0 ? "-" : "+";
  const absOffset = Math.abs(offset);
  const hours = Math.trunc(absOffset / 60);
  const minutes = absOffset % 60;
  if (minutes === 0) {
    return sign + String(hours);
  }
  return sign + String(hours) + delimiter + addLeadingZeros(minutes, 2);
}
function formatTimezoneWithOptionalMinutes(offset, delimiter) {
  if (offset % 60 === 0) {
    const sign = offset > 0 ? "-" : "+";
    return sign + addLeadingZeros(Math.abs(offset) / 60, 2);
  }
  return formatTimezone(offset, delimiter);
}
function formatTimezone(offset, delimiter = "") {
  const sign = offset > 0 ? "-" : "+";
  const absOffset = Math.abs(offset);
  const hours = addLeadingZeros(Math.trunc(absOffset / 60), 2);
  const minutes = addLeadingZeros(absOffset % 60, 2);
  return sign + hours + delimiter + minutes;
}
const dateLongFormatter = (pattern, formatLong2) => {
  switch (pattern) {
    case "P":
      return formatLong2.date({ width: "short" });
    case "PP":
      return formatLong2.date({ width: "medium" });
    case "PPP":
      return formatLong2.date({ width: "long" });
    case "PPPP":
    default:
      return formatLong2.date({ width: "full" });
  }
};
const timeLongFormatter = (pattern, formatLong2) => {
  switch (pattern) {
    case "p":
      return formatLong2.time({ width: "short" });
    case "pp":
      return formatLong2.time({ width: "medium" });
    case "ppp":
      return formatLong2.time({ width: "long" });
    case "pppp":
    default:
      return formatLong2.time({ width: "full" });
  }
};
const dateTimeLongFormatter = (pattern, formatLong2) => {
  const matchResult = pattern.match(/(P+)(p+)?/) || [];
  const datePattern = matchResult[1];
  const timePattern = matchResult[2];
  if (!timePattern) {
    return dateLongFormatter(pattern, formatLong2);
  }
  let dateTimeFormat;
  switch (datePattern) {
    case "P":
      dateTimeFormat = formatLong2.dateTime({ width: "short" });
      break;
    case "PP":
      dateTimeFormat = formatLong2.dateTime({ width: "medium" });
      break;
    case "PPP":
      dateTimeFormat = formatLong2.dateTime({ width: "long" });
      break;
    case "PPPP":
    default:
      dateTimeFormat = formatLong2.dateTime({ width: "full" });
      break;
  }
  return dateTimeFormat.replace("{{date}}", dateLongFormatter(datePattern, formatLong2)).replace("{{time}}", timeLongFormatter(timePattern, formatLong2));
};
const longFormatters = {
  p: timeLongFormatter,
  P: dateTimeLongFormatter
};
const dayOfYearTokenRE = /^D+$/;
const weekYearTokenRE = /^Y+$/;
const throwTokens = ["D", "DD", "YY", "YYYY"];
function isProtectedDayOfYearToken(token) {
  return dayOfYearTokenRE.test(token);
}
function isProtectedWeekYearToken(token) {
  return weekYearTokenRE.test(token);
}
function warnOrThrowProtectedError(token, format2, input) {
  const _message = message(token, format2, input);
  console.warn(_message);
  if (throwTokens.includes(token))
    throw new RangeError(_message);
}
function message(token, format2, input) {
  const subject = token[0] === "Y" ? "years" : "days of the month";
  return `Use \`${token.toLowerCase()}\` instead of \`${token}\` (in \`${format2}\`) for formatting ${subject} to the input \`${input}\`; see: https://github.com/date-fns/date-fns/blob/master/docs/unicodeTokens.md`;
}
const formattingTokensRegExp = /[yYQqMLwIdDecihHKkms]o|(\w)\1*|''|'(''|[^'])+('|$)|./g;
const longFormattingTokensRegExp = /P+p+|P+|p+|''|'(''|[^'])+('|$)|./g;
const escapedStringRegExp = /^'([^]*?)'?$/;
const doubleQuoteRegExp = /''/g;
const unescapedLatinCharacterRegExp = /[a-zA-Z]/;
function format(date, formatStr, options) {
  var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r;
  const defaultOptions2 = getDefaultOptions();
  const locale = (_b = (_a = options == null ? void 0 : options.locale) != null ? _a : defaultOptions2.locale) != null ? _b : enUS;
  const firstWeekContainsDate = (_j = (_i = (_f = (_e = options == null ? void 0 : options.firstWeekContainsDate) != null ? _e : (_d = (_c = options == null ? void 0 : options.locale) == null ? void 0 : _c.options) == null ? void 0 : _d.firstWeekContainsDate) != null ? _f : defaultOptions2.firstWeekContainsDate) != null ? _i : (_h = (_g = defaultOptions2.locale) == null ? void 0 : _g.options) == null ? void 0 : _h.firstWeekContainsDate) != null ? _j : 1;
  const weekStartsOn = (_r = (_q = (_n = (_m = options == null ? void 0 : options.weekStartsOn) != null ? _m : (_l = (_k = options == null ? void 0 : options.locale) == null ? void 0 : _k.options) == null ? void 0 : _l.weekStartsOn) != null ? _n : defaultOptions2.weekStartsOn) != null ? _q : (_p = (_o = defaultOptions2.locale) == null ? void 0 : _o.options) == null ? void 0 : _p.weekStartsOn) != null ? _r : 0;
  const originalDate = toDate(date, options == null ? void 0 : options.in);
  if (!isValid(originalDate)) {
    throw new RangeError("Invalid time value");
  }
  let parts = formatStr.match(longFormattingTokensRegExp).map((substring) => {
    const firstCharacter = substring[0];
    if (firstCharacter === "p" || firstCharacter === "P") {
      const longFormatter = longFormatters[firstCharacter];
      return longFormatter(substring, locale.formatLong);
    }
    return substring;
  }).join("").match(formattingTokensRegExp).map((substring) => {
    if (substring === "''") {
      return { isToken: false, value: "'" };
    }
    const firstCharacter = substring[0];
    if (firstCharacter === "'") {
      return { isToken: false, value: cleanEscapedString(substring) };
    }
    if (formatters[firstCharacter]) {
      return { isToken: true, value: substring };
    }
    if (firstCharacter.match(unescapedLatinCharacterRegExp)) {
      throw new RangeError(
        "Format string contains an unescaped latin alphabet character `" + firstCharacter + "`"
      );
    }
    return { isToken: false, value: substring };
  });
  if (locale.localize.preprocessor) {
    parts = locale.localize.preprocessor(originalDate, parts);
  }
  const formatterOptions = {
    firstWeekContainsDate,
    weekStartsOn,
    locale
  };
  return parts.map((part) => {
    if (!part.isToken)
      return part.value;
    const token = part.value;
    if (!(options == null ? void 0 : options.useAdditionalWeekYearTokens) && isProtectedWeekYearToken(token) || !(options == null ? void 0 : options.useAdditionalDayOfYearTokens) && isProtectedDayOfYearToken(token)) {
      warnOrThrowProtectedError(token, formatStr, String(date));
    }
    const formatter = formatters[token[0]];
    return formatter(originalDate, token, locale.localize, formatterOptions);
  }).join("");
}
function cleanEscapedString(input) {
  const matched = input.match(escapedStringRegExp);
  if (!matched) {
    return input;
  }
  return matched[1].replace(doubleQuoteRegExp, "'");
}
function formatDistance(laterDate, earlierDate, options) {
  var _a, _b;
  const defaultOptions2 = getDefaultOptions();
  const locale = (_b = (_a = options == null ? void 0 : options.locale) != null ? _a : defaultOptions2.locale) != null ? _b : enUS;
  const minutesInAlmostTwoDays = 2520;
  const comparison = compareAsc(laterDate, earlierDate);
  if (isNaN(comparison))
    throw new RangeError("Invalid time value");
  const localizeOptions = Object.assign({}, options, {
    addSuffix: options == null ? void 0 : options.addSuffix,
    comparison
  });
  const [laterDate_, earlierDate_] = normalizeDates(
    options == null ? void 0 : options.in,
    ...comparison > 0 ? [earlierDate, laterDate] : [laterDate, earlierDate]
  );
  const seconds = differenceInSeconds(earlierDate_, laterDate_);
  const offsetInSeconds = (getTimezoneOffsetInMilliseconds(earlierDate_) - getTimezoneOffsetInMilliseconds(laterDate_)) / 1e3;
  const minutes = Math.round((seconds - offsetInSeconds) / 60);
  let months;
  if (minutes < 2) {
    if (options == null ? void 0 : options.includeSeconds) {
      if (seconds < 5) {
        return locale.formatDistance("lessThanXSeconds", 5, localizeOptions);
      } else if (seconds < 10) {
        return locale.formatDistance("lessThanXSeconds", 10, localizeOptions);
      } else if (seconds < 20) {
        return locale.formatDistance("lessThanXSeconds", 20, localizeOptions);
      } else if (seconds < 40) {
        return locale.formatDistance("halfAMinute", 0, localizeOptions);
      } else if (seconds < 60) {
        return locale.formatDistance("lessThanXMinutes", 1, localizeOptions);
      } else {
        return locale.formatDistance("xMinutes", 1, localizeOptions);
      }
    } else {
      if (minutes === 0) {
        return locale.formatDistance("lessThanXMinutes", 1, localizeOptions);
      } else {
        return locale.formatDistance("xMinutes", minutes, localizeOptions);
      }
    }
  } else if (minutes < 45) {
    return locale.formatDistance("xMinutes", minutes, localizeOptions);
  } else if (minutes < 90) {
    return locale.formatDistance("aboutXHours", 1, localizeOptions);
  } else if (minutes < minutesInDay) {
    const hours = Math.round(minutes / 60);
    return locale.formatDistance("aboutXHours", hours, localizeOptions);
  } else if (minutes < minutesInAlmostTwoDays) {
    return locale.formatDistance("xDays", 1, localizeOptions);
  } else if (minutes < minutesInMonth) {
    const days = Math.round(minutes / minutesInDay);
    return locale.formatDistance("xDays", days, localizeOptions);
  } else if (minutes < minutesInMonth * 2) {
    months = Math.round(minutes / minutesInMonth);
    return locale.formatDistance("aboutXMonths", months, localizeOptions);
  }
  months = differenceInMonths(earlierDate_, laterDate_);
  if (months < 12) {
    const nearestMonth = Math.round(minutes / minutesInMonth);
    return locale.formatDistance("xMonths", nearestMonth, localizeOptions);
  } else {
    const monthsSinceStartOfYear = months % 12;
    const years = Math.trunc(months / 12);
    if (monthsSinceStartOfYear < 3) {
      return locale.formatDistance("aboutXYears", years, localizeOptions);
    } else if (monthsSinceStartOfYear < 9) {
      return locale.formatDistance("overXYears", years, localizeOptions);
    } else {
      return locale.formatDistance("almostXYears", years + 1, localizeOptions);
    }
  }
}
function formatDistanceToNow(date, options) {
  return formatDistance(date, constructNow(date), options);
}
var Contents = {
  data: null,
  _fetch: null,
  load: function(id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }
    if (this._fetch) {
      return this._fetch;
    }
    this._fetch = mithril.request({ method: "GET", url: `api/contents` }).then((result) => {
      this.data = result;
      this._fetch = null;
    }).catch((err) => {
      this._fetch = null;
      throw err;
    });
  },
  reset: function() {
    this.data = null;
    this._fetch = null;
  }
};
const getLanguages = (content) => {
  const languages = /* @__PURE__ */ new Set();
  switch (content == null ? void 0 : content.app_mode) {
    case "jupyter-static":
    case "jupyter-static":
    case "python-api":
    case "python-bokeh":
    case "python-dash":
    case "python-fastapi":
    case "python-gradio":
    case "python-shiny":
    case "python-streamlit":
    case "tensorflow-saved-model":
      languages.add("Python");
      break;
    case "quarto-shiny":
    case "quarto-static":
      languages.add("Quarto");
      break;
    case "rmd-shiny":
    case "rmd-static":
    case "shiny":
      languages.add("R");
      break;
    case "static":
      languages.add("Static");
      break;
  }
  switch (content == null ? void 0 : content.content_category) {
    case "plot":
      languages.add("Static");
      languages.add("Plot");
      break;
    case "pin":
      languages.add("Static");
      languages.add("Pin");
      break;
    case "rmd-static":
      languages.add("Static");
      languages.add("Site");
      break;
  }
  if (content["r_version"] != null && content["r_version"] !== "") {
    languages.add("R");
  }
  if (content["py_version"] != null && content["py_version"] !== "") {
    languages.add("Python");
  }
  if (content["quarto_version"] != null && content["quarto_version"] !== "") {
    languages.add("Quarto");
  }
  if (content["content_category"] === "pin") {
    languages.add("Pin");
  }
  return [...languages].sort();
};
var Languages = {
  view: function(vnode2) {
    const languages = getLanguages(vnode2.attrs);
    return languages.map((language) => {
      return mithril("span", { class: "mx-1 badge text-bg-primary" }, language);
    });
  }
};
const Content = {
  data: null,
  _fetch: null,
  load: function(id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }
    if (this._fetch) {
      return this._fetch;
    }
    this._fetch = mithril.request({ method: "GET", url: `api/contents/${id}` }).then((result) => {
      this.data = result;
      this._fetch = null;
    }).catch((err) => {
      this._fetch = null;
      throw err;
    });
  },
  delete: function(content_id) {
    return mithril.request({
      method: "DELETE",
      url: `api/contents/${content_id}`
    });
  },
  reset: function() {
    this.data = null;
    this._fetch = null;
  }
};
const reloadContents = () => {
  try {
    Contents.reset();
    Contents.load();
  } catch (err) {
    console.error(err, "Failed to reload contents.");
  }
};
const ConfirmDeleteButton = {
  view(vnode2) {
    return mithril(
      "button",
      {
        class: "btn btn-primary",
        ariaLabel: "Yes",
        "data-bs-dismiss": "modal",
        onclick: () => {
          Content.delete(vnode2.attrs.contentId);
          reloadContents();
        }
      },
      "Yes"
    );
  }
};
const CancelDeleteButton = {
  view(_vnode) {
    return mithril(
      "button",
      {
        class: "btn btn-secondary",
        ariaLabel: "No",
        "data-bs-dismiss": "modal"
      },
      "No"
    );
  }
};
const DeleteModal = {
  view: function(vnode2) {
    return mithril("div", { class: "modal", id: `deleteModal-${vnode2.attrs.contentId}`, tabindex: "-1", ariaHidden: true }, [
      mithril("div", { class: "modal-dialog modal-dialog-centered" }, [
        mithril("div", { class: "modal-content" }, [
          mithril("div", { class: "modal-header" }, [
            mithril("h1", { class: "modal-title fs-6" }, "Delete Content"),
            mithril("button", {
              class: "btn-close",
              ariaLabel: "Close modal",
              "data-bs-dismiss": "modal"
            })
          ]),
          mithril("section", { class: "modal-body" }, [
            mithril("p", {
              id: "modal-message",
              class: "mb-3"
            }, `Are you sure you want to delete ${vnode2.attrs.contentTitle}?`)
          ]),
          mithril("div", { class: "modal-footer" }, [
            mithril(CancelDeleteButton),
            mithril(ConfirmDeleteButton, { contentId: vnode2.attrs.contentId })
          ])
        ])
      ])
    ]);
  }
};
const ContentsComponent = {
  error: null,
  oninit: () => {
    try {
      Contents.load();
    } catch (err) {
      globalThis.error = "Failed to load data.";
      console.error(err);
    }
  },
  view: () => {
    if (globalThis.error) {
      return mithril("div", { class: "error" }, globalThis.error);
    }
    const contents = Contents.data;
    if (contents === null) {
      return;
    }
    if (contents.length === 0) {
      return "";
    }
    return mithril(
      "table",
      { class: "table" },
      mithril(
        "thead",
        mithril("tr", [
          mithril("th", { scope: "col" }, "Title"),
          mithril("th", { scope: "col" }, "Language"),
          mithril("th", { scope: "col" }, "Running Processes"),
          mithril("th", { scope: "col" }, "Last Updated"),
          mithril("th", { scope: "col" }, "Date Added"),
          mithril("th", { scope: "col" }, ""),
          mithril("th", { scope: "col" }, "")
        ])
      ),
      mithril(
        "tbody",
        Contents.data.map((content) => {
          var _a;
          const guid = content["guid"];
          const title = content["title"];
          return mithril(
            "tr",
            [
              mithril(
                "td",
                {
                  class: "link-primary content-page-link",
                  onclick: () => mithril.route.set(`/contents/${guid}`)
                },
                title || mithril("i", "No Name")
              ),
              mithril(
                "td",
                mithril(Languages, content)
              ),
              mithril("td", (_a = content == null ? void 0 : content.active_jobs) == null ? void 0 : _a.length),
              mithril("td", format(content["last_deployed_time"], "MMM do, yyyy")),
              mithril("td", format(content["created_time"], "MMM do, yyyy")),
              mithril(
                "td",
                mithril("button", {
                  class: "action-btn",
                  "data-bs-toggle": "modal",
                  "data-bs-target": `#deleteModal-${guid}`
                }, [
                  mithril("i", { class: "fa-solid fa-trash" })
                ])
              ),
              mithril(
                "td",
                mithril("a", {
                  class: "fa-solid fa-arrow-up-right-from-square",
                  href: content["content_url"],
                  target: "_blank",
                  onclick: (e) => e.stopPropagation()
                })
              ),
              mithril(DeleteModal, {
                contentId: guid,
                contentTitle: title
              })
            ]
          );
        })
      )
    );
  }
};
const Home = {
  view: function() {
    return mithril(
      "div",
      mithril("h1", "Content"),
      mithril(
        "p",
        { class: "text-secondary" },
        "Manage your content and their settings here."
      ),
      mithril(ContentsComponent)
    );
  }
};
const About = {
  error: null,
  oninit: function(vnode2) {
    try {
      Content.load(vnode2.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load author.";
      console.error(err);
    }
  },
  onremove: function() {
    Content.reset();
  },
  view: function(vnode2) {
    if (this.error) {
      return mithril("div", { class: "error" }, this.error);
    }
    const content = Content.data;
    if (content === null) {
      return "";
    }
    const desc = content == null ? void 0 : content.description;
    const updated = content == null ? void 0 : content.last_deployed_time;
    const created = content == null ? void 0 : content.created_time;
    return mithril(".pt-3.border-top", [
      mithril(".", [
        mithril("h5", "About"),
        mithril("p", desc || mithril("i", "No Description")),
        mithril(
          "p",
          mithril(
            "small.text-body-secondary",
            "Updated " + formatDistanceToNow(updated, { addSuffix: true })
          )
        ),
        mithril(
          "p",
          mithril(
            "small.text-body-secondary",
            "Created on " + format(created, "MMMM do, yyyy")
          )
        )
      ])
    ]);
  }
};
var Releases$1 = {
  data: null,
  _fetch: null,
  load: function(id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }
    if (this._fetch) {
      return this._fetch;
    }
    this._fetch = mithril.request({ method: "GET", url: `api/contents/${id}/releases` }).then((result) => {
      this.data = result;
      this._fetch = null;
    }).catch((err) => {
      this._fetch = null;
      throw err;
    });
  },
  reset: function() {
    this.data = null;
    this._fetch = null;
  }
};
const Release = {
  view: function(vnode2) {
    var _a, _b, _c;
    return mithril(".row.my-3", [
      mithril(".d-flex.align-items-center", [
        mithril("i.fa-solid.fa-code-commit.me-1"),
        mithril(".font-monospace", (_a = vnode2.attrs) == null ? void 0 : _a.id),
        ((_b = vnode2.attrs) == null ? void 0 : _b.active) ? mithril("i.fa-regular.fa-circle-check.ms-1.text-success") : ""
      ]),
      mithril(
        "small.text-secondary",
        format((_c = vnode2.attrs) == null ? void 0 : _c.created_time, "MMM do, yyyy")
      )
    ]);
  }
};
var Releases = {
  error: null,
  oninit: function(vnode2) {
    try {
      Releases$1.load(vnode2.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load releases.";
      console.error(err);
    }
  },
  onremove: function() {
    Releases$1.reset();
  },
  view: function() {
    if (this.error) {
      return mithril("div", { class: "error" }, this.error);
    }
    const releases = Releases$1.data;
    if (releases === null) {
      return;
    }
    if (releases.length === 0) {
      return;
    }
    let recent = releases.slice(0, 3);
    recent = recent.map((release) => {
      return mithril(Release, release);
    });
    let old = releases.slice(3);
    old = old.map((release) => {
      return mithril(Release, release);
    });
    if (old.length === 0) {
      old = "";
    } else {
      old = [
        mithril(
          "",
          {
            class: "text-secondary",
            type: "button",
            "data-bs-toggle": "collapse",
            "data-bs-target": "#old",
            onclick: (e) => {
              const icon = e.target.querySelector("i") || e.target;
              const currentRotation = icon.style.transform === "rotate(90deg)" ? "rotate(0deg)" : "rotate(90deg)";
              icon.style.transform = currentRotation;
              icon.style.transition = "transform 0.3s ease";
            }
          },
          mithril("i", { class: "fa-solid fa-ellipsis" })
        ),
        mithril("div", { class: "collapse", id: "old" }, old)
      ];
    }
    return mithril(".pt-3.border-top", [
      mithril(".", [
        mithril("h5", [
          "Releases ",
          mithril("span.badge.rounded-pill.text-bg-secondary", releases.length)
        ]),
        recent,
        old
      ])
    ]);
  }
};
const Processes$1 = {
  data: null,
  _fetch: null,
  load: function(id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }
    if (this._fetch) {
      return this._fetch;
    }
    this._fetch = mithril.request({ method: "GET", url: `api/contents/${id}/processes` }).then((result) => {
      this.data = result;
      this._fetch = null;
    }).catch((err) => {
      this._fetch = null;
      throw err;
    });
  },
  destroy: function(content_id, process_id) {
    return mithril.request({
      method: "DELETE",
      url: `api/contents/${content_id}/processes/${process_id}`
    });
  },
  reset: function() {
    this.data = null;
    this._fetch = null;
  }
};
const StopButton = {
  oninit(vnode2) {
    vnode2.state.isHovered = false;
    vnode2.state.disabled = false;
  },
  view(vnode2) {
    return mithril(
      "button",
      {
        class: "btn btn-link text-danger p-0",
        disabled: vnode2.state.disabled,
        onclick: () => {
          if (vnode2.state.disabled) {
            return;
          }
          vnode2.state.disabled = true;
          mithril.redraw();
          console.log(`Stopping process ${vnode2.attrs.process_id}`);
          Processes$1.destroy(
            vnode2.attrs.content_id,
            vnode2.attrs.process_id
          ).then(() => {
            console.log(`Stopped process ${vnode2.attrs.process_id}`);
            Processes$1.reset();
            return Processes$1.load();
          }).then(() => {
            mithril.redraw();
          }).catch((err) => {
            console.error("Failed to reload processes:", err);
            vnode2.state.disabled = false;
            mithril.redraw();
          });
        },
        title: "Stop Process",
        onmouseover: () => {
          vnode2.state.isHovered = true;
          mithril.redraw();
        },
        onmouseout: () => {
          vnode2.state.isHovered = false;
          mithril.redraw();
        }
      },
      mithril(
        `i.${vnode2.state.isHovered ? "fa-solid" : "fa-regular"}.fa-circle-stop`,
        {
          style: "font-size: 1.2rem;"
        }
      )
    );
  }
};
var Processes = {
  error: null,
  oninit: function(vnode2) {
    try {
      Processes$1.load(vnode2.attrs.id);
    } catch (err) {
      this.error = "Failed to load data.";
      console.error(err);
    }
  },
  onremove: function(vnode2) {
    Processes$1.reset();
  },
  view: function(vnode2) {
    if (this.error) {
      return mithril("div", { class: "error" }, this.error);
    }
    const processes = Processes$1.data;
    if (processes === null || processes.length === 0) {
      return mithril(".pt-3.border-top", [
        mithril("h5", "Processes"),
        mithril("p.text-dark", "There are no server processes running at this time...")
      ]);
    }
    return mithril(".pt-3.border-top", [
      mithril("h5", "Processes"),
      mithril(
        "table.table",
        mithril(
          "thead",
          mithril("tr", [
            mithril("th", { scope: "col" }, ""),
            mithril("th", { scope: "col" }, "Id"),
            mithril("th", { scope: "col" }, "Started"),
            mithril("th", { scope: "col" }, "Hostname")
          ])
        ),
        mithril(
          "tbody",
          processes.map((process) => {
            return mithril("tr.align-items-center", [
              mithril(
                "td.text-center.py-2",
                mithril(StopButton, {
                  content_id: vnode2.attrs.id,
                  process_id: process == null ? void 0 : process.key
                })
              ),
              mithril("td", process == null ? void 0 : process.pid),
              mithril(
                "td",
                formatDistanceToNow(process == null ? void 0 : process.start_time, { addSuffix: true })
              ),
              mithril("td", process == null ? void 0 : process.hostname)
            ]);
          })
        )
      )
    ]);
  }
};
const Author$1 = {
  data: null,
  _fetch: null,
  load: function(id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }
    if (this._fetch) {
      return this._fetch;
    }
    this._fetch = mithril.request({ method: "GET", url: `api/contents/${id}/author` }).then((result) => {
      this.data = result;
      this._fetch = null;
    }).catch((err) => {
      this._fetch = null;
      throw err;
    });
  },
  reset: function() {
    this.data = null;
    this._fetch = null;
  }
};
var Author = {
  error: null,
  oninit: function(vnode2) {
    try {
      Author$1.load(vnode2.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load author.";
      console.error(err);
    }
  },
  onremove: function() {
    Author$1.reset();
  },
  view: function(vnode2) {
    if (this.error) {
      return mithril("div", { class: "error" }, this.error);
    }
    const author = Author$1.data;
    if (author === null) {
      return "";
    }
    return mithril(".pt-3.border-top", [
      mithril(".", [
        mithril("h5", "Author"),
        mithril("p", (author == null ? void 0 : author.first_name) + " " + (author == null ? void 0 : author.last_name)),
        mithril(
          "p",
          mithril("small.text-body-secondary.align-items-center", [
            mithril(".fa-regular.fa-at"),
            " ",
            author == null ? void 0 : author.username
          ])
        ),
        mithril(
          "p",
          mithril("small.text-body-secondary.align-items-center", [
            mithril(".fa-regular.fa-envelope"),
            " ",
            mithril("a", { href: `mailto:${author == null ? void 0 : author.email}` }, author == null ? void 0 : author.email)
          ])
        ),
        mithril(
          "p",
          mithril("small.text-body-secondary", [
            "Active ",
            formatDistanceToNow(author == null ? void 0 : author.active_time, { addSuffix: true })
          ])
        )
      ])
    ]);
  }
};
var Collaborators = {
  view: function() {
    const content = Content.data;
    const accessUrl = (content == null ? void 0 : content.dashboard_url) ? `${content.dashboard_url}/access` : "#";
    return mithril(".pt-3.border-top", [
      mithril(".", [
        mithril("h5", "Collaborators"),
        mithril(
          "p",
          mithril("small.text-body-secondary.align-items-center", [
            mithril(".fa-solid.fa-user-lock"),
            " ",
            mithril("a", { href: accessUrl, target: "_blank" }, "See Collaborators and Manage Access")
          ])
        )
      ])
    ]);
  }
};
const Edit = {
  error: null,
  oninit: function(vnode2) {
    try {
      Content.load(vnode2.attrs.id);
    } catch (err) {
      this.error = "Failed to load data.";
      console.error(err);
    }
  },
  onremove: function() {
    Content.reset();
  },
  view: function(vnode2) {
    if (this.error) {
      return mithril("div", { class: "error" }, this.error);
    }
    const content = Content.data;
    if (content === null) {
      return "";
    }
    return mithril(
      "div",
      mithril(".d-flex.flex-row.justify-content-between.align-items-center.my-3", [
        mithril("h2.mb-0", (content == null ? void 0 : content.title) || mithril("i", "No Name")),
        mithril(
          "a.btn.btn-lg.btn-outline-primary.d-flex.align-items-center.justify-content-center.gap-2",
          {
            href: content == null ? void 0 : content.dashboard_url,
            target: "_blank"
          },
          ["Open in Connect", mithril("i.fa-solid.fa-arrow-up-right-from-square")]
        )
      ]),
      mithril(".row", mithril(".pb-3", mithril(Languages, content))),
      mithril(".row.", [
        mithril(".col-8", [
          mithril(
            ".pt-3.pb-3.border-top",
            mithril("iframe", {
              src: content == null ? void 0 : content.content_url,
              width: "100%",
              style: { minHeight: "50vh" },
              frameborder: "0",
              allowfullscreen: true,
              class: "border border-bottom-0 border-light rounded p-1"
            })
          ),
          mithril(Processes, { id: vnode2.attrs.id })
        ]),
        mithril(".col-4", [
          mithril(About, {
            desc: content == null ? void 0 : content.description,
            updated: content == null ? void 0 : content.last_deployed_time,
            created: content == null ? void 0 : content.created_time
          }),
          mithril(Author, {
            content_id: content == null ? void 0 : content.guid
          }),
          mithril(Collaborators, {
            content_id: content == null ? void 0 : content.guid
          }),
          mithril(Releases, {
            content_id: content == null ? void 0 : content.guid
          })
        ])
      ])
    );
  }
};
var Layout = {
  view: (vnode2) => {
    return mithril("div", [
      mithril("nav.navbar.navbar-expand-lg.bg-light", [
        mithril("div.container-xxl", [
          mithril(
            "a.navbar-brand",
            {
              style: { cursor: "pointer" },
              onclick: () => mithril.route.set(`/`)
            },
            "Publisher Command Center"
          ),
          mithril("ul.navbar-nav.me-auto", [
            mithril(
              "li.nav-item",
              mithril(
                "a.nav-link",
                {
                  style: { cursor: "pointer" },
                  onclick: () => mithril.route.set("/contents")
                },
                "Content"
              )
            )
          ])
        ])
      ]),
      mithril("div.container-xxl", vnode2.children)
    ]);
  }
};
const root = document.getElementById("app");
mithril.request({ method: "GET", url: "api/auth-status" }).then((res) => {
  if (!res.authorized) {
    mithril.mount(root, {
      view: () => mithril(
        "div.alert.alert-info",
        { style: { margin: "1rem" } },
        [
          mithril("p", [
            "To finish setting up this content, you must add a Visitor API Key ",
            "integration with the Publisher scope."
          ]),
          mithril("p", [
            'Select "+ Add integration" in the Access settings panel to the ',
            'right, and find an entry with "Authentication type: Visitor API Key".'
          ]),
          mithril("p", [
            "If no such integration exists, an Administrator must configure one. ",
            "Go to Connect's System page, select the Integrations tab, then ",
            'click "+ Add Integration", choose "Connect API", pick Publisher or ',
            "Administrator under Max Role, and give it a descriptive title."
          ])
        ]
      )
    });
  } else {
    mithril.route(root, "/contents", {
      "/contents": {
        render: () => mithril(Layout, mithril(Home))
      },
      "/contents/:id": {
        render: (vnode2) => mithril(Layout, mithril(Edit, vnode2.attrs))
      }
    });
  }
}).catch((err) => {
  console.error("failed to fetch auth-status", err);
});
