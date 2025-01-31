import os
import argparse
import symfem
from datetime import datetime
from symfem import create_element
from builder import plotting, settings
from builder.markup import markup, insert_links, python_highlight, cap_first
from builder.examples import markup_example
from builder.citations import markup_citation, make_bibtex
from builder.element import Categoriser
from builder.html import make_html_page
from builder.snippets import parse_example
from builder.families import (arnold_logg_name, cockburn_fu_name,
                              arnold_logg_reference, cockburn_fu_reference)
from builder.rss import make_rss

start_all = datetime.now()

parser = argparse.ArgumentParser(description="Build defelement.com")
parser.add_argument('destination', metavar='destination', nargs="?",
                    default=None, help="Destination of HTML files.")
parser.add_argument('--test', metavar="test", default=None,
                    help="Builds a version of the website with fewer elements.")
parser.add_argument('--github-token', metavar="github_token", default=None,
                    help="Provide a GitHub token to get update timestamps.")
parser.add_argument('--processes', metavar="processes", default=None,
                    help="The number of processes to run the building of examples on.")


args = parser.parse_args()
if args.destination is not None:
    settings.html_path = args.destination
    settings.htmlelement_path = os.path.join(settings.html_path, "elements")
    settings.htmlimg_path = os.path.join(settings.html_path, "img")
    settings.htmlindices_path = os.path.join(settings.html_path, "lists")
    settings.htmlfamilies_path = os.path.join(settings.html_path, "families")

if args.processes is not None:
    settings.processes = int(args.processes)

if args.github_token is not None:
    settings.github_token = args.github_token

if args.test is None:
    test_elements = None
elif args.test == "auto":
    test_elements = [
        "buffa-christiansen", "direct-serendipity", "dual", "hellan-herrmann-johnson",
        "hsieh-clough-tocher", "lagrange", "nedelec1", "raviart-thomas", "regge",
        "serendipity", "taylor-hood", "vector-bubble-enriched-Lagrange", "enriched-galerkin"]
else:
    test_elements = args.test.split(",")

# Prepare paths
if os.path.isdir(settings.html_path):
    os.system(f"rm -rf {settings.html_path}")
os.mkdir(settings.html_path)
os.mkdir(settings.htmlelement_path)
os.mkdir(settings.htmlindices_path)
os.mkdir(settings.htmlfamilies_path)
os.mkdir(settings.htmlimg_path)
os.system(f"cp -r {settings.dir_path}/people {settings.htmlimg_path}")
os.mkdir(os.path.join(settings.htmlelement_path, "bibtex"))
os.mkdir(os.path.join(settings.htmlelement_path, "examples"))

os.system(f"cp -r {settings.files_path}/* {settings.html_path}")

with open(os.path.join(settings.html_path, "CNAME"), "w") as f:
    f.write("defelement.com")

# Make pages
for file in os.listdir(settings.pages_path):
    if file.endswith(".md"):
        start = datetime.now()
        fname = file[:-3]
        print(f"{fname}.html", end="", flush=True)
        with open(os.path.join(settings.pages_path, file)) as f:
            content = markup(f.read())

        with open(os.path.join(settings.html_path, f"{fname}.html"), "w") as f:
            f.write(make_html_page(content))
        end = datetime.now()
        print(f" (completed in {(end - start).total_seconds():.2f}s)")

# Load categories and reference elements
categoriser = Categoriser()
categoriser.load_categories(os.path.join(settings.data_path, "categories"))
categoriser.load_references(os.path.join(settings.data_path, "references"))
categoriser.load_families(os.path.join(settings.data_path, "families"))
categoriser.load_implementations(os.path.join(settings.data_path, "implementations"))

# Load elements from .def files
categoriser.load_folder(settings.element_path)

cdescs = {
    "L2": "Discontinuous.",
    "H1": "Function values are continuous.",
    "H2": "Function values and derivatives are continuous.",
    "H3": "Function values and first and second derivatives are continuous.",
    "H(div)": "Components normal to facets are continuous",
    "H(curl)": "Components tandential to facets are continuous",
    "H(div div)": "Inner products with normals to facets are continuous",
    "H(curl curl)": "Inner products with tangents to facets are continuous"}

# Generate element pages
all_examples = []
for e in categoriser.elements:
    print(e.name)
    content = f"<h1>{cap_first(e.html_name)}</h1>"
    element_data = []
    implementations = []

    # Link to ciarlet.html
    content += "<p><small><a href='/ciarlet.html'>"
    content += "Click here to read what the information on this page means."
    content += "</a></small></p>"

    # Alternative names
    alt_names = e.alternative_names(include_exterior=False)
    if len(alt_names) > 0:
        element_data.append(("Alternative names", ", ".join(alt_names)))
    al_names = e.arnold_logg_names()
    if len(al_names) > 0:
        element_data.append(("Exterior calculus names", ", ".join(al_names)))
    cf_names = e.cockburn_fu_names()
    if len(cf_names) > 0:
        element_data.append(("Cockburn&ndash;fu names", ", ".join(cf_names)))

    # Short names
    short_names = e.short_names()
    if len(short_names) > 0:
        element_data.append(("Abbreviated names", ", ".join(short_names)))

    # Orders
    element_data.append(("Orders", e.order_range()))

    # Reference elements
    refs = e.reference_elements()
    element_data.append(("Reference elements", ", ".join(refs)))

    # Mixed elements
    if e.is_mixed:
        subelements = e.sub_elements()
        element_data.append(
            ("Definition",
             "This is a mixed element containing these subelements:"
             "<ul>" + "\n".join(subelements) + "</ul>"))

    # Polynomial set
    psets = e.make_polynomial_set_html()
    if len(psets) > 0:
        element_data.append(("Polynomial set", psets))

    # DOFs
    dofs = e.make_dof_descriptions()
    if len(dofs) > 0:
        element_data.append(("DOFs", dofs))

    # Number of DOFs
    ndofs = e.dof_counts()
    if len(ndofs) > 0:
        element_data.append(("Number of DOFs", ndofs))

    # Number of DOFs on subentities
    ndofs = e.entity_dof_counts()
    if len(ndofs) > 0:
        element_data.append(("Number of DOFs<breakable>on subentities", ndofs))

    # Mapping
    mapping = e.mapping()
    if mapping is not None:
        element_data.append(("Mapping", mapping))

    # Continuity
    sobolev = e.sobolev()
    if sobolev is not None:
        if isinstance(sobolev, dict):
            element_data.append(("continuity", "<br />".join([
                f"{cdescs[c]} (\\({n}\\))" for n, c in sobolev.items()])))
        else:
            element_data.append(("continuity", cdescs[sobolev]))

    # Notes
    notes = e.notes
    if len(notes) > 0:
        element_data.append(
            ("Notes", "<br />\n".join([insert_links(i) for i in notes])))

    # Implementations
    libraries = [
        (i, j["name"], j["url"], j["install"])
        for i, j in categoriser.implementations.items()
    ]
    libraries.sort(key=lambda i: i[0])
    for codename, libname, url, pip in libraries:
        if e.implemented(codename):
            info = e.list_of_implementation_strings(codename)

            if e.has_implementation_examples(codename):

                info += "<br />"

                info += f"<a class='show_eg_link' id='show_{codename}_link' "
                info += f"href='javascript:show_{codename}_eg()'"
                info += " style='display:block'>"
                info += f"&darr; Show {libname} examples &darr;</a>"
                info += f"<a class='hide_eg_link' id='hide_{codename}_link' "
                info += f"href='javascript:hide_{codename}_eg()'"
                info += " style='display:none'>"
                info += f"&uarr; Hide {libname} examples &uarr;</a>"
                info += f"<div id='{codename}_eg' style='display:none'>"
                info += "Before trying this example, you must install "
                info += f"<a href='{url}'>{libname}</a>"
                if pip is None:
                    info += ". "
                else:
                    info += f":<p class='pcode'>{pip}</p>"
                info += "This element can then be created with the following lines of Python:"

                info += "<p class='pcode'>" + python_highlight(
                    e.make_implementation_examples(codename)) + "</p>"
                info += "</div>"
                info += "<script type='text/javascript'>\n"
                info += f"function show_{codename}_eg(){{\n"
                info += f" document.getElementById('show_{codename}_link').style.display='none'\n"
                info += f" document.getElementById('hide_{codename}_link').style.display='block'\n"
                info += f" document.getElementById('{codename}_eg').style.display='block'\n"
                info += "}\n"
                info += f"function hide_{codename}_eg(){{\n"
                info += f" document.getElementById('show_{codename}_link').style.display='block'\n"
                info += f" document.getElementById('hide_{codename}_link').style.display='none'\n"
                info += f" document.getElementById('{codename}_eg').style.display='none'\n"
                info += "}\n"
                info += "</script>"

            implementations.append(
                (f"<a href='/lists/implementations/{libname}.html'>{libname}</a>", info))

    # Categories
    cats = e.categories()
    if len(cats) > 0:
        element_data.append(("Categories", ", ".join(cats)))

    # Write element data
    content += "<table class='element-info'>"
    for i, j in element_data:
        content += f"<tr><td>{i.replace(' ', '&nbsp;').replace('<breakable>', ' ')}</td>"
        content += f"<td>{j}</td></tr>"
    content += "</table>"

    # Write implementations
    if len(implementations) > 0:
        content += "<h2>Implementations</h2>\n"
        content += "<table class='element-info'>"
        for i, j in implementations:
            content += f"<tr><td>{i.replace(' ', '&nbsp;')}</td><td>{j}</td></tr>"
        content += "</table>"

    # Write examples using symfem
    if e.has_examples:
        element_examples = []

        if test_elements is None or e.filename in test_elements:
            assert e.implemented("symfem")

            for eg in e.examples:
                cell, order, kwargs = parse_example(eg)
                symfem_name, params = e.get_implementation_string("symfem", cell)

                fname = f"{cell}-{symfem_name}-{order}.html"
                for s in " ()":
                    fname = fname.replace(s, "-")

                name = f"{cell}<br />order {order}"
                for i, j in kwargs.items():
                    name += f"<br />{i}={str(j).replace(' ', '&nbsp;')}"

                eginfo = {
                    "name": name, "args": [cell, symfem_name, order], "kwargs": kwargs,
                    "html_name": e.html_name, "element_filename": e.html_filename,
                    "filename": fname, "url": f"/elements/examples/{fname}"}
                if "variant" in params:
                    eginfo["kwargs"]["variant"] = params["variant"]
                all_examples.append(eginfo)
                element_examples.append(eginfo)

        if len(element_examples) > 0:
            content += "<h2>Examples</h2>\n"
            content += "<table class='element-info'>"
            for eg in element_examples:
                element = create_element(*eg['args'], **eg['kwargs'])
                content += (
                    f"<tr><td>{eg['name']}</td><td><center><a href='{eg['url']}'>"
                    f"{plotting.plot_dof_diagram(element, link=False)}"
                    "<br /><small>(click to view basis functions)</small></a></center></td></tr>")
            content += "</table>"

    # Write references section
    refs = e.references()
    if len(al_names) > 0:
        refs.append(arnold_logg_reference)
    if len(cf_names) > 0:
        refs.append(cockburn_fu_reference)
    if len(refs) > 0:
        content += "<h2>References</h2>\n"
        content += "<ul class='citations'>\n"
        for i, r in enumerate(refs):
            content += f"<li>{markup_citation(r)}"
            content += f" [<a href='/elements/bibtex/{e.filename}-{i}.bib'>BibTeX</a>]</li>\n"
            with open(os.path.join(settings.htmlelement_path,
                                   f"bibtex/{e.filename}-{i}.bib"), "w") as f:
                f.write(make_bibtex(f"{e.filename}-{i}", r))
        content += "</ul>"

    # Write created and updated dates
    if e.created is not None:
        content += "<h2>DefElement stats</h2>\n"
        content += "<table class='element-info'>"
        content += f"<tr><td>Element&nbsp;added</td><td>{e.created.strftime('%d %B %Y')}</td></tr>"
        content += "<tr><td>Element&nbsp;last&nbsp;updated</td>"
        content += f"<td>{e.modified.strftime('%d %B %Y')}</td></tr>"
        content += "</table>"

    # Write file
    with open(os.path.join(settings.htmlelement_path, e.html_filename), "w") as f:
        f.write(make_html_page(content, e.html_name))


def build_examples(egs, process=""):
    for eg in egs:
        start = datetime.now()

        element = create_element(*eg['args'], **eg['kwargs'])

        markup_example(
            element, eg['html_name'], f"/elements/{eg['element_filename']}",
            eg['filename'])

        end = datetime.now()
        print(f"  {process}{eg['args'][0]} {eg['args'][1]} {eg['args'][2]}"
              f" (completed in {(end - start).total_seconds():.2f}s)", flush=True)


# Make example pages
print("Making examples")
if settings.processes == 1:
    build_examples(all_examples)
else:
    import multiprocessing

    p = settings.processes
    n_egs = len(all_examples)

    jobs = []
    for i in range(p):
        process = multiprocessing.Process(
            target=build_examples,
            args=(all_examples[n_egs * i // p: n_egs * (i + 1) // p], f"[{i}] ")
        )
        jobs.append(process)

    for j in jobs:
        j.start()

    for j in jobs:
        j.join()

# Index page
content = "<h1>Index of elements</h1>\n"
# Generate filtering Javascript
content += "<script type='text/javascript'>\n"
content += "function do_filter_refall(){\n"
content += "    if(document.getElementById('check-ref-all').checked){\n"
for r in categoriser.references:
    content += f"        document.getElementById('check-ref-{r}').checked = false\n"
content += "    }\n"
content += "    do_filter()\n"
content += "}\n"
content += "function do_filter_catall(){\n"
content += "    if(document.getElementById('check-cat-all').checked){\n"
for c in categoriser.categories:
    content += f"        document.getElementById('check-cat-{c}').checked = false\n"
content += "    }\n"
content += "    do_filter()\n"
content += "}\n"
content += "function do_filter_cat(){\n"
content += "    if(document.getElementById('check-cat-all').checked){\n"
content += "        if("
content += " || ".join([f"document.getElementById('check-cat-{c}').checked"
                        for c in categoriser.categories])
content += "){"
content += "            document.getElementById('check-cat-all').checked = false\n"
content += "        }\n"
content += "    }\n"
content += "    do_filter()\n"
content += "}\n"
content += "function do_filter_ref(){\n"
content += "    if(document.getElementById('check-ref-all').checked){\n"
content += "        if("
content += " || ".join([f"document.getElementById('check-ref-{r}').checked"
                        for r in categoriser.references])
content += "){"
content += "            document.getElementById('check-ref-all').checked = false\n"
content += "        }\n"
content += "    }\n"
content += "    do_filter()\n"
content += "}\n"
content += "function do_filter(){\n"
content += "    var els = document.getElementsByClassName('element-on-list')\n"
content += "    for(var i=0; i < els.length; i++){\n"
content += "        var ref_show = false\n"
content += "        if(document.getElementById('check-ref-all').checked){\n"
content += "            ref_show = true\n"
content += "        } else {\n"
for r in categoriser.references:

    content += f"            if(document.getElementById('check-ref-{r}').checked"
    content += f" && els[i].id.indexOf('ref-{r}') != -1){{ref_show = true}}\n"
content += "        }\n"
content += "        var cat_show = false\n"
content += "        if(document.getElementById('check-cat-all').checked){\n"
content += "            cat_show = true\n"
content += "        } else {\n"
for c in categoriser.categories:

    content += f"            if(document.getElementById('check-cat-{c}').checked"
    content += f" && els[i].id.indexOf('cat-{c}') != -1){{cat_show = true}}\n"
content += "        }\n"
content += "        if(cat_show && ref_show){\n"
content += "            els[i].style.display='block'\n"
content += "        } else {\n"
content += "            els[i].style.display='none'\n"
content += "        }\n"
content += "    }\n"
content += "}\n"
content += "function show_filtering(){\n"
content += "    document.getElementById('show-flink').style.display='none'\n"
content += "    document.getElementById('hide-flink').style.display='block'\n"
content += "    document.getElementById('the-filters').style.display='block'\n"
content += "}\n"
content += "function hide_filtering(){\n"
content += "    document.getElementById('show-flink').style.display='block'\n"
content += "    document.getElementById('hide-flink').style.display='none'\n"
content += "    document.getElementById('the-filters').style.display='none'\n"
content += "}\n"
content += "</script>"
content += "<a href='javascript:show_filtering()' id='show-flink' style='display:block'"
content += ">&darr; Show filters &darr;</a>\n"
content += "<a href='javascript:hide_filtering()' id='hide-flink' style='display:none'"
content += ">&uarr; Hide filters &uarr;</a>\n"
content += "<table id='the-filters' class='filters' style='display:none'>"
content += "<tr><td>Reference&nbsp;elements</td><td>"
content += "<label><input type='checkbox' checked id='check-ref-all' onchange='do_filter_refall()'"
content += ">&nbsp;show all</label> "
for r in categoriser.references:
    content += f"<label><input type='checkbox' id='check-ref-{r}' onchange='do_filter_ref()'"
    content += f">&nbsp;{r}</label> "
content += "</td></tr>"
content += "<tr><td>Categories</td><td>"
content += "<label><input type='checkbox' checked id='check-cat-all'onchange='do_filter_catall()'"
content += ">&nbsp;show all</label> "
for c in categoriser.categories:
    content += f"<label><input type='checkbox' id='check-cat-{c}'onchange='do_filter_cat()'"
    content += f">&nbsp;{categoriser.get_category_name(c)}</label> "
content += "</td></tr>"
content += "</table>\n"
# Write element list
elementlist = []
for e in categoriser.elements:
    id = " ".join([f"ref-{r}" for r in e.reference_elements(False)]
                  + [f"cat-{c}" for c in e.categories(False, False)])
    for name in [e.html_name] + e.alternative_names(False, False, False, True):
        elementlist.append((name.lower(),
                            f"<li class='element-on-list' id='{id}'>"
                            f"<a href='/elements/{e.html_filename}'>{name}</a></li>"))
elementlist.sort(key=lambda x: x[0])
content += "<ul>" + "\n".join([i[1] for i in elementlist]) + "</ul>"

with open(os.path.join(settings.htmlelement_path, "index.html"), "w") as f:
    f.write(make_html_page(content))
with open(os.path.join(settings.htmlindices_path, "index.html"), "w") as f:
    f.write(make_html_page(content))

# Recently updated elements
rss_icon = ("<span style='color:#FF8800;padding-left:10px'>"
            "<i class='fa fa-rss' aria-hidden='true'></i></span>")
content = "<h1>Recent elements</h1>\n"
content += f"<h2>Recently added elements <a href='/new-elements.xml'>{rss_icon}</a></h2>\n"
content += "<ul>\n"
for e in categoriser.recently_added(10):
    content += f"<li><a href='/elements/{e.html_filename}'>{e.html_name}</a>"
    if e.created is not None:
        content += f" ({e.created.strftime('%d %B %Y')})"
    content += "</li>\n"
content += "</ul>\n"

content += f"<h2>Recently updated elements <a href='/updated-elements.xml'>{rss_icon}</a></h2>\n"
content += "<ul>\n"
for e in categoriser.recently_updated(10):
    content += f"<li><a href='/elements/{e.html_filename}'>{e.html_name}</a>"
    if e.modified is not None:
        content += f" ({e.modified.strftime('%d %B %Y')})"
    content += "</li>\n"
content += "</ul>\n"

with open(os.path.join(settings.htmlindices_path, "recent.html"), "w") as f:
    f.write(make_html_page(content))

with open(os.path.join(settings.html_path, "new-elements.xml"), "w") as f:
    f.write(make_rss(categoriser.recently_added(10), "recently added elements",
                     "Finite elements that have recently been added to DefElement",
                     "created"))

with open(os.path.join(settings.html_path, "updated-elements.xml"), "w") as f:
    f.write(make_rss(categoriser.recently_updated(10), "recently updated elements",
                     "Finite element whose pages on DefElement have recently been updated",
                     "modified"))

# Category index
os.mkdir(os.path.join(settings.htmlindices_path, "categories"))
content = "<h1>Categories</h1>\n"
for c in categoriser.categories:
    category_pages = []
    for e in categoriser.elements_in_category(c):
        for name in [e.html_name] + e.alternative_names(False, False, False, True):
            category_pages.append((name.lower(),
                                   f"<li><a href='/elements/{e.html_filename}'>{name}</a></li>"))

    category_pages.sort(key=lambda x: x[0])

    content += (f"<h2><a href='/lists/categories/{c}.html'>{categoriser.get_category_name(c)}"
                "</a></h2>\n<ul>")
    content += "".join([i[1] for i in category_pages])
    content += "</ul>"

    sub_content = f"<h1>{categoriser.get_category_name(c)}</h1>\n<ul>"
    sub_content += "".join([i[1] for i in category_pages])
    sub_content += "</ul>"

    with open(os.path.join(settings.htmlindices_path, f"categories/{c}.html"), "w") as f:
        f.write(make_html_page(sub_content))

with open(os.path.join(settings.htmlindices_path, "categories/index.html"), "w") as f:
    f.write(make_html_page(content))

# Implementations index
os.mkdir(os.path.join(settings.htmlindices_path, "implementations"))
content = "<h1>Implemented elements</h1>\n"
for c, info in categoriser.implementations.items():
    category_pages = []
    for e in categoriser.elements_in_implementation(c):
        names = {e.html_name}
        refs = set()
        for cname in categoriser.references:
            for i_str in e.list_of_implementation_strings(c, None):
                if "(" not in i_str or f"({cname})" in i_str:
                    refs.add(cname)
                    break
        for r in refs:
            for name in e.alternative_names(False, False, False, True, r):
                names.add(name)
        for name in names:
            category_pages.append((name.lower(),
                                   f"<li><a href='/elements/{e.html_filename}'>{name}</a></li>"))

    category_pages.sort(key=lambda x: x[0])

    content += (f"<h2><a href='/lists/implementations/{c}.html'>Implemented in {info['name']}"
                "</a></h2>\n<ul>")
    content += "".join([i[1] for i in category_pages])
    content += "</ul>"

    sub_content = f"<h1>Implemented in <a href='{info['url']}'>{info['name']}</a></h1>\n<ul>"
    sub_content += "".join([i[1] for i in category_pages])
    sub_content += "</ul>"

    with open(os.path.join(settings.htmlindices_path, f"implementations/{c}.html"), "w") as f:
        f.write(make_html_page(sub_content))

with open(os.path.join(settings.htmlindices_path, "implementations/index.html"), "w") as f:
    f.write(make_html_page(content))

# Reference elements index
os.mkdir(os.path.join(settings.htmlindices_path, "references"))
content = "<h1>Reference elements</h1>\n"
for c in categoriser.references:
    refels = []
    for e in categoriser.elements_by_reference(c):
        for name in [e.html_name] + e.alternative_names(False, False, False, True, c):
            refels.append((name.lower(),
                           f"<li><a href='/elements/{e.html_filename}'>{name}</a></li>"))

    refels.sort(key=lambda x: x[0])

    content += f"<h2><a href='/lists/references/{c}.html'></a>{cap_first(c)}</h2>\n"
    content += "<ul>" + "".join([i[1] for i in refels]) + "</ul>"

    sub_content = "<h1>Finite elements on a"
    if c[0] in "aeiou":
        sub_content += "n"
    sub_content += f" {c}</h1>\n"
    sub_content += "<ul>" + "".join([i[1] for i in refels]) + "</ul>"

    with open(os.path.join(settings.htmlindices_path, f"references/{c}.html"), "w") as f:
        f.write(make_html_page(sub_content))

with open(os.path.join(settings.htmlindices_path, "references/index.html"), "w") as f:
    f.write(make_html_page(content))

# Page shoeing numbering of references
content = "<h1>Reference cell numbering</h1>"
content += "<p>This page illustrates the entity numbering used for each reference cell.</p>"
for cell in categoriser.references.keys():
    if cell == "dual polygon":
        for i in [4, 5, 6]:
            content += f"<h2>Dual polygon ({i})</h2>"
            content += plotting.plot_reference(symfem.create_reference(f"dual polygon({i})"))
    else:
        content += f"<h2>{cell[0].upper()}{cell[1:]}</h2>"
        content += plotting.plot_reference(symfem.create_reference(cell))

with open(os.path.join(settings.html_path, "reference_numbering.html"), "w") as f:
    f.write(make_html_page(content))

# Families
content = "<h1>De Rham families</h1>\n"
content += "<p>You can find some information about how these familes are defined "
content += "<a href='/de-rham.html'>here</a></p>"
content += "<table class='families'>\n"
content += "<tr>"
content += "<td><small>Exterior calculus name</small></td>"
content += "<td><small>Cockburn&ndash;Fu name</small></td>"
content += "<td>\\(H^k\\)</td>"
content += "<td>\\(\\xrightarrow{\\nabla}\\)</td>"
content += "<td>\\(H^{k-1}(\\textbf{curl})\\)</td>"
content += "<td>\\(\\xrightarrow{\\nabla\\times}\\)</td>"
content += "<td>\\(H^{k-1}(\\text{div})\\)</td>"
content += "<td>\\(\\xrightarrow{\\nabla\\cdot}\\)</td>"
content += "<td>\\(H^{k-1}\\)</td>"
content += "</tr>\n"
for fname, data in categoriser.exterior_families.items():
    family = data["elements"]

    names = []
    if "arnold-logg" in data:
        names.append("\\(" + arnold_logg_name(data['arnold-logg']) + "\\)")
    if "cockburn-fu" in data:
        names.append("\\(" + cockburn_fu_name(data['cockburn-fu']) + "\\)")
    if len(names) == 0:
        raise ValueError(f"No name found for family: {fname}")
    sub_content = "<h1>The " + " / ".join(names) + " family</h1>"

    assert len([i for i in ["simplex", "tp"] if i in family]) == 1

    sub_content += "<ul>"
    for cell in ["simplex", "tp"]:
        if cell in family:
            content += "<tr>"
            if "arnold-logg" in data:
                content += f"<td><a href='/families/{fname}.html'>\\("
                content += arnold_logg_name(data['arnold-logg'], cell=cell)
                content += "\\)</td>"
            else:
                content += "<td>&nbsp;</td>"
            if "cockburn-fu" in data:
                content += f"<td><a href='/families/{fname}.html'>\\("
                content += cockburn_fu_name(data['cockburn-fu'], cell=cell)
                content += "\\)</td>"
            else:
                content += "<td>&nbsp;</td>"
            for order in ["0", "1", "d-1", "d"]:
                if order in family[cell]:
                    sub_content += f"<li><a href='/elements/{family[cell][order][1]}'"
                    sub_content += " style='text-decoration:none'>"
                    names = []
                    if "arnold-logg" in data:
                        names.append("\\(" + arnold_logg_name(data['arnold-logg'],
                                                              order, cell) + "\\)")
                    if "cockburn-fu" in data:
                        names.append("\\(" + cockburn_fu_name(data['cockburn-fu'],
                                                              order, cell) + "\\)")
                    sub_content += " / ".join(names)
                    sub_content += f" ({family[cell][order][0]})</a></li>"
                    content += f"<td><a href='/elements/{family[cell][order][1]}'"
                    content += " style='text-decoration:none'>"
                    content += f"{family[cell][order][0]}</a></td>"
                else:
                    content += "<td>&nbsp;</td>"
                if order != "d":
                    content += "<td>&nbsp;</td>"
            content += "</tr>"
        sub_content += "</ul>"

    with open(os.path.join(settings.htmlfamilies_path, f"{fname}.html"), "w") as f:
        f.write(make_html_page(sub_content))

content += "</table>"
with open(os.path.join(settings.htmlfamilies_path, "index.html"), "w") as f:
    f.write(make_html_page(content))

# List of lists
content = "<h1>Lists of elements</h1>\n<ul>\n"
content += "<li><a href='/lists/categories'>Finite elements by category</a></li>\n"
content += "<li><a href='/lists/references'>Finite elements by reference element</a></li>\n"
content += "<li><a href='/lists/recent.html'>Recently added/updated finite elements</a></li>\n"
content += "</ul>"
with open(os.path.join(settings.htmlindices_path, "index.html"), "w") as f:
    f.write(make_html_page(content))

end_all = datetime.now()
print(f"Total time: {(end_all - start_all).total_seconds():.2f}s")
