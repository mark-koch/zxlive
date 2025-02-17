import copy
from typing import Iterator

from PySide6.QtWidgets import QToolButton
from pyzx import VertexType, to_gh, basicrules
from pyzx.graph.base import BaseGraph, VT

from .base_panel import BasePanel, ToolbarSection
from .commands import MoveNode, SetGraph, AddIdentity, ChangeColor
from .graphscene import GraphScene
from .rules import bialgebra


class ProofPanel(BasePanel):
    """Panel for the proof mode of ZX live."""

    def __init__(self, graph: BaseGraph) -> None:
        self.graph_scene = GraphScene()
        self.graph_scene.vertices_moved.connect(self._vert_moved)
        super().__init__(graph, self.graph_scene)

    def _toolbar_sections(self) -> Iterator[ToolbarSection]:
        fuse = QToolButton(self, text="Fuse")
        identity_z = QToolButton(self, text="Z identity")
        identity_x = QToolButton(self, text="X identity")
        color_change = QToolButton(self, text="Color change")
        bialgebra = QToolButton(self, text="Bialgebra")
        strong_comp = QToolButton(self, text="Strong comp")
        gh_state = QToolButton(self, text="To GH form")

        fuse.clicked.connect(self._fuse_clicked)
        identity_z.clicked.connect(lambda: self._identity_clicked(VertexType.Z))
        identity_x.clicked.connect(lambda: self._identity_clicked(VertexType.X))
        color_change.clicked.connect(self._color_change_clicked)
        bialgebra.clicked.connect(self._bialgebra_clicked)
        strong_comp.clicked.connect(self._strong_comp_clicked)
        gh_state.clicked.connect(self._gh_state_clicked)

        yield ToolbarSection(fuse, identity_z, identity_x, color_change, bialgebra,
                             strong_comp, gh_state, exclusive=True)

    def _vert_moved(self, vs: list[tuple[VT, float, float]]) -> None:
        cmd = MoveNode(self.graph_view, vs)
        self.undo_stack.push(cmd)

    def _fuse_clicked(self):
        vs = list(self.graph_scene.selected_vertices)
        self.graph_scene.clearSelection()

        if vs == []:
            self.graph_view.set_graph(self.graph)
            return

        new_g = copy.deepcopy(self.graph)

        if len(vs) == 1:
            basicrules.remove_id(new_g, vs[0])
            cmd = SetGraph(self.graph_view, new_g)
            self.undo_stack.push(cmd)
            return

        x_vertices = [v for v in vs if self.graph.type(v) == VertexType.X]
        z_vertices = [v for v in vs if self.graph.type(v) == VertexType.Z]
        vs = [x_vertices, z_vertices]
        fuse = False
        for lst in vs:
            lst = sorted(lst)
            to_fuse = {}
            visited = set()
            for v in lst:
                if v in visited:
                    continue
                to_fuse[v] = []
                # dfs
                stack = [v]
                while stack:
                    u = stack.pop()
                    if u in visited:
                        continue
                    visited.add(u)
                    for w in self.graph.neighbors(u):
                        if w in lst:
                            to_fuse[v].append(w)
                            stack.append(w)

            for v in to_fuse:
                for w in to_fuse[v]:
                    basicrules.fuse(new_g, v, w)
                    fuse = True

        if not fuse:
            self.graph_view.set_graph(self.graph)
            return

        cmd = SetGraph(self.graph_view, new_g)
        self.undo_stack.push(cmd)

    def _strong_comp_clicked(self):
        new_g = copy.deepcopy(self.graph)
        selected = list(self.graph_scene.selected_vertices)
        if len(selected) != 2:
            return
        self.graph_scene.clearSelection()
        v1, v2 = selected
        if basicrules.check_strong_comp(new_g, v1, v2):
            basicrules.strong_comp(new_g, v1, v2)
            cmd = SetGraph(self.graph_view, new_g)
            self.undo_stack.push(cmd)

    def _bialgebra_clicked(self):
        # TODO: Maybe replace copy with more efficient undo?
        new_g = copy.deepcopy(self.graph)
        selected = list(self.graph_scene.selected_vertices)
        if len(selected) < 2:
            return
        bialgebra(new_g, selected)
        self.graph_scene.clearSelection()
        cmd = SetGraph(self.graph_view, new_g)
        self.undo_stack.push(cmd)

    def _gh_state_clicked(self):
        # TODO: Do we want to respect selection here?
        new_g = copy.deepcopy(self.graph)
        to_gh(new_g)
        cmd = SetGraph(self.graph_view, new_g)
        self.graph_scene.clearSelection()
        self.undo_stack.push(cmd)

    def _identity_clicked(self, vty: VertexType) -> None:
        selected = list(self.graph_scene.selected_vertices)
        if len(selected) != 2:
            return
        u, v = selected
        if not self.graph.connected(u, v):
            return
        cmd = AddIdentity(self.graph_view, u, v, vty)
        self.undo_stack.push(cmd)

    def _color_change_clicked(self) -> None:
        cmd = ChangeColor(self.graph_view, list(self.graph_scene.selected_vertices))
        self.graph_scene.clearSelection()
        self.undo_stack.push(cmd)
