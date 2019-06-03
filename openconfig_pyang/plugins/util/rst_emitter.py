"""
Copyright 2015 Google, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Implements a Markdown documentation emitter for YANG modules

"""

from .doc_emitter import DocEmitter
from . import yangpath
from .yangdoc_defs import YangDocDefs


def h(content, symbol):
    return "{}\n{}\n".format(content, symbol * len(content))


def h1(content):
    return h(content, "#")


def h2(content):
    return h(content, "*")


def h3(content):
    return h(content, "=")


def h4(content):
    return h(content, "-")


def h5(content):
    return h(content, "^")


def h6(content):
    return h(content, '"')


def b(content):
    return "**{}**".format(content)


def i(content):
    return "*{}*".format(content)


def c(content):
    return "``{}``".format(content)


def block(content):
    return "\n{}\n\n".format(content)


def newline():
    return "\n"


def separator():
    return "\n\n-----\n\n"


class RSTEmitter(DocEmitter):
    def genModuleDoc(self, mod, ctx):
        # emit top level module info
        s = h1(mod.module_name)
        s += block(mod.module.attrs.get("desc", ""))

        # handle typedefs
        if len(mod.typedefs) > 0:
            s += h3("Types")
            for typename, td in mod.typedefs.items():
                s += h4(typename)
                s += block(td.attrs.get("desc", ""))
                s += block(b("type") + ": " + c(td.typedoc.typename))
                for k, v in td.typedoc.attrs.get("enums", {}).items():
                    s += block("* {}: {}".format(c(k), v))
                restrictions = td.typedoc.attrs.get("restrictions")
                if restrictions:
                    for k, v in restrictions.items():
                        s += block("{}: {}".format(b(k), c(v)))
                if td.typedoc.typename == "union":
                    for childtype in td.typedoc.childtypes:
                        s += gen_type_info(childtype, is_union=True)

        # handle identities
        if len(mod.identities) > 0:
            s += h3("Identities")
            for base_id in mod.base_identities:
                s += h4("base: " + i(base_id))
                s += block(mod.identities[base_id].attrs["desc"])
                # collect all of the identities that have base_id as
                # their base
                derived = {
                    key: value
                    for key, value in mod.identities.items()
                    if value.attrs["base"] == base_id
                }
                # emit the identities derived from the current base
                for idname, id in derived.items():
                    s += h4(idname)
                    s += block(b("base identity") + ": " + id.attrs["base"])
                    s += block(id.attrs["desc"])

        if len(mod.module.children) > 0:
            s += h3("Data nodes")

        self.moduledocs[mod.module_name] = s

    def genStatementDoc(self, statement, ctx, level=1):
        """Markdown emitter method for YANG statements"""

        s = ""
        if ctx.opts.strip_namespace:
            pathstr = yangpath.strip_namespace(statement.attrs["path"])
        else:
            pathstr = statement.attrs["path"]

        # for 'skipped' nodes, just print the path
        if statement.keyword in self.path_only:
            s += h4(pathstr)
            return s

        s += h4("{}".format(pathstr))

        if "desc" in statement.attrs:
            s += block(statement.attrs["desc"])

        s += b("nodetype") + ": " + c(statement.keyword)
        if statement.attrs["is_key"]:
            s += " (list key)"
        s += newline()

        if statement.typedoc:
            s += gen_type_info(statement.typedoc)

        s += separator()

        self.moduledocs[statement.module_doc.module_name] += s

    def emitDocs(self, ctx, section=None):
        """Return the HTML output for all modules,
    or single section if specified"""

        docs = []
        # create the documentation elements for each module
        for module_name in self.moduledocs:
            docs.append(self.moduledocs[module_name])

        if ctx.opts.doc_title is None:
            s = ""
        else:
            s = h1(ctx.opts.doc_title)

        for d in docs:
            s += "{}\n\n".format(d)
        return s


def gen_type_info(typedoc, is_union=False):
    """Create and return documentation based on the type.  Expands compound
  types."""
    b_prefix = "*  " if is_union else ""
    prefix = "  " if is_union else ""
    s = block("{}{}: {}".format(b_prefix, b("Type"), c(typedoc.typename)))

    typename = typedoc.typename
    if typename == "enumeration":
        for enum, desc in typedoc.attrs["enums"].items():
            s += block("{}* {}: {}".format(prefix, c(enum), desc))
    elif typename == "string":
        if "pattern" in typedoc.attrs["restrictions"]:
            s += block(
                "{}* {}: {}".format(
                    prefix, b("pattern"), c(typedoc.attrs["restrictions"]["pattern"])
                )
            )
    elif typename in YangDocDefs.integer_types:
        if "range" in typedoc.attrs["restrictions"]:
            s += block(
                "{}* {}: {}".format(
                    prefix, b("range"), c(typedoc.attrs["restrictions"]["range"])
                )
            )
    elif typename == "identityref":
        s += block("{}* {}: {}".format(prefix, b("base"), c(typedoc.attrs["base"])))
    elif typename == "leafref":
        s += block(
            "{}* {}: {}".format(
                prefix, b("path reference"), c(typedoc.attrs["leafref_path"])
            )
        )
    elif typename == "union":
        for childtype in typedoc.childtypes:
            s += gen_type_info(childtype, is_union=True)
    else:
        pass

    return s
