import os
from collections import defaultdict
from os import path
from typing import Any, Dict, Tuple
import shutil

import yaml
from docutils import nodes
from docutils.io import StringOutput
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import SEP, ensuredir

THEME = "sphinx-guru"

logger = logging.getLogger(__name__)


class GuruBuilder(StandaloneHTMLBuilder):
    name = "guru"
    epilog = __("The Guru pages are in %(outdir)s.")
    resources_path = "resources"

    def init(self) -> None:
        self.search = False
        self.build_info = self.create_build_info()
        # basename of images directory
        self.imagedir = self.resources_path
        # section numbers for headings in the currently visited document
        self.secnumbers = {}  # type: Dict[str, Tuple[int, ...]]
        # currently written docname
        self.current_docname = None  # type: str

        self.copysource = False

        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()

        html_file_suffix = self.get_builder_config("file_suffix", "html")
        if html_file_suffix is not None:
            self.out_suffix = html_file_suffix

        html_link_suffix = self.get_builder_config("link_suffix", "html")
        if html_link_suffix is not None:
            self.link_suffix = html_link_suffix
        else:
            self.link_suffix = self.out_suffix

        self.use_index = self.get_builder_config("use_index", "html")

    def add_sidebars(self, pagename: str, ctx: Dict) -> None:
        return

    def finish(self) -> None:
        self.finish_tasks.add_task(self.gen_additional_pages)
        self.finish_tasks.add_task(self.copy_image_files)
        self.finish_tasks.add_task(self.copy_download_files)
        self.finish_tasks.add_task(self.copy_extra_files)
        self.finish_tasks.add_task(self.write_buildinfo)
        self.write_entity_definition(".", "collection", {"Tags": []})
        self.write_boards()
        archive_path = path.join(self.outdir, "..", "guru.zip")
        if path.exists(archive_path):
            os.unlink(archive_path)

        shutil.make_archive(
            archive_path.replace(".zip", ""), "zip", root_dir=self.outdir, base_dir="."
        )

    def get_target_uri(self, docname: str, typ: str = None) -> str:
        if docname == "index":
            return ""
        if docname.endswith(SEP + "index"):
            return docname[:-5]  # up to sep
        return docname + SEP

    @staticmethod
    def get_entity_id(pagename: str):
        return pagename.replace(SEP, "-")

    def get_outfilename(self, pagename: str) -> str:
        return path.join(
            self.outdir, "cards", self.get_entity_id(pagename) + self.out_suffix
        )

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        destination = StringOutput(encoding="utf-8")
        doctree.settings = self.docsettings

        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})
        self.imgpath = self.resources_path
        self.dlpath = self.resources_path
        self.current_docname = docname

        if (
            doctree.children
            and doctree.children[0].children
            and doctree.children[0].children[0].tagname == "title"
        ):
            # Removing the h1 header to avoid having it duplicated.
            doctree.children[0].children.pop(0)

        self.docwriter.write(doctree, destination)
        self.docwriter.assemble_parts()
        body = self.docwriter.parts["fragment"]
        metatags = self.docwriter.clean_meta

        base_docname = os.path.basename(docname)
        if base_docname != "index":
            ctx = self.get_doc_context(docname, body, metatags)
            if self.config.html_published_location and doctree.children:
                ctx["source_url"] = self.build_external_url(docname)
            self.handle_page(docname, ctx, event_arg=doctree)
            self.write_card_definition(docname)

    def build_external_url(self, docname: str) -> str:
        prefix = self.config.html_published_location
        if not prefix:
            return ""
        return path.join(prefix, f"{docname}.html")

    def write_card_definition(self, docname: str) -> None:
        directory = os.path.dirname(docname)
        tags = directory.split(SEP)

        properties = {
            "Title": self.get_title(docname),
            "Tags": [f"Engineering:{tag}" for tag in tags],
            "ExternalId": docname,
            "ExternalUrl": self.build_external_url(docname),
        }

        self.write_entity_definition("cards", docname.replace(SEP, "-"), properties)

    def write_entity_definition(
        self, entity_type: str, entity_name: str, properties: Dict[str, any]
    ):
        outdirname = path.join(self.outdir, entity_type)
        outfilename = path.join(outdirname, entity_name + ".yaml")
        ensuredir(outdirname)
        try:
            with open(
                outfilename, "w", encoding="utf-8", errors="xmlcharrefreplace"
            ) as f:
                yaml.safe_dump(properties, stream=f)
        except OSError as err:
            logger.warning(__("error writing file %s: %s"), outfilename, err)

    def get_theme_config(self) -> Tuple[str, Dict]:
        return THEME, {}

    def write_boards(self) -> None:
        groups = defaultdict(list)
        for name, pages in self.env.toctree_includes.items():
            if any([not page.endswith("/index") for page in pages]):
                groups[name.split(SEP)[0]].append(name.replace("/index", ""))

        for group_name, boards in groups.items():
            if len(boards) <= 1:
                continue

            group = {
                "Title": self.get_title(path.join(group_name, "index")),
                "Description": "",
                "Boards": [self.get_entity_id(board) for board in boards],
                "ExternalId": group_name,
                "ExternalUrl": self.build_external_url("index"),
            }
            self.write_entity_definition(
                "board-groups", self.get_entity_id(group_name), group
            )

        for name, pages in self.env.toctree_includes.items():
            title = []
            name_segments = name.split(SEP)
            if len(name_segments) > 1:
                for i, _ in enumerate(name_segments[:-2], 1):
                    title.append(
                        self.get_title(path.join(*name_segments[0:i], "index"))
                    )
            title.append(self.get_title(name))

            items = [
                {"ID": self.get_entity_id(page), "Type": "card"}
                for page in pages
                if not page.endswith("/index")
            ]

            if not items:
                continue

            board = {
                "Title": " - ".join(title),
                "Description": "",
                "Items": items,
                "ExternalId": name,
                "ExternalUrl": self.build_external_url(name),
            }
            self.write_entity_definition(
                "boards", self.get_entity_id(path.dirname(name)), board
            )

    def get_title(self, docname) -> str:
        return str(self.env.titles[docname].children[0])


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_builder(GuruBuilder)

    theme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "theme"))
    app.add_html_theme(THEME, theme_path)
    app.add_config_value("html_published_location", "", "guru")

    return {"version": "0.0.1", "parallel_read_safe": True, "parallel_write_safe": True}
