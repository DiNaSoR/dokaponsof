from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dokapon_explorer.report import write_json_report, write_logic_report, write_markdown_report
from dokapon_explorer.workbench import build_atlas_for_document, list_cell_files, load_cell_document, render_map_image, scan_workspace


class ScrollableImage(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background="#f7f1e3", highlightthickness=0)
        self.x_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.y_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.x_scroll.set, yscrollcommand=self.y_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.y_scroll.grid(row=0, column=1, sticky="ns")
        self.x_scroll.grid(row=1, column=0, sticky="ew")
        self._photo: ImageTk.PhotoImage | None = None

    def set_image(self, image) -> None:
        self.canvas.delete("all")
        self._photo = None
        if image is None:
            self.canvas.configure(scrollregion=(0, 0, 0, 0))
            return
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))


class DevToolsApp:
    def __init__(self, root: tk.Tk, game_dir: Path | None) -> None:
        self.root = root
        self.root.title("Dokapon Development Kit")
        self.root.geometry("1580x980")
        self.root.minsize(1280, 840)

        self.game_dir_var = tk.StringVar(value=str(game_dir) if game_dir else "")
        self.status_var = tk.StringVar(value="Ready.")
        self.file_filter_var = tk.StringVar(value="")
        self.palette_var = tk.StringVar(value="0")

        self.cell_files: list[Path] = []
        self.filtered_files: list[Path] = []
        self.current_document = None
        self.current_atlas = None
        self.current_map_image = None
        self.current_scan_debug = None
        self.current_scan_groups = None

        self._configure_style()
        self._build_ui()

        if game_dir is not None:
            self.scan_game()

    def _configure_style(self) -> None:
        self.root.configure(background="#cbbda6")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=("Segoe UI", 10))
        style.configure("Root.TFrame", background="#cbbda6")
        style.configure("Panel.TFrame", background="#efe6d4")
        style.configure("Card.TFrame", background="#f7f1e3", relief="flat")
        style.configure("Title.TLabel", background="#cbbda6", foreground="#3f301b", font=("Bahnschrift SemiBold", 18))
        style.configure("Subtitle.TLabel", background="#cbbda6", foreground="#5c4a2c", font=("Segoe UI Semibold", 10))
        style.configure("PanelTitle.TLabel", background="#efe6d4", foreground="#4d3d25", font=("Bahnschrift SemiBold", 11))
        style.configure("Body.TLabel", background="#efe6d4", foreground="#302718")
        style.configure("Status.TLabel", background="#6c5938", foreground="#fff8ec", font=("Segoe UI Semibold", 9))
        style.configure("Tool.TButton", padding=(12, 6), font=("Segoe UI Semibold", 9))
        style.configure("Treeview", rowheight=24, fieldbackground="#fbf7ef", background="#fbf7ef", foreground="#2d2417")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#e0d2b9", foreground="#3f311d")
        style.map("Treeview", background=[("selected", "#b69e6a")], foreground=[("selected", "#1f160a")])
        style.configure("TNotebook", background="#efe6d4", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 7), font=("Segoe UI Semibold", 9))
        style.map("TNotebook.Tab", background=[("selected", "#f7f1e3"), ("!selected", "#d9c9aa")], foreground=[("selected", "#3d2e17")])

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        header = ttk.Frame(outer, style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="DOKAPON DEVELOPMENT KIT", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Map logic, tile atlases, records, and reverse-engineering workspace", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))

        toolbar = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(14, 14))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Game Directory", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        entry = ttk.Entry(toolbar, textvariable=self.game_dir_var)
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Button(toolbar, text="Browse", style="Tool.TButton", command=self.choose_game_dir).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(toolbar, text="Scan Workspace", style="Tool.TButton", command=self.scan_game).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(toolbar, text="Write Reports", style="Tool.TButton", command=self.write_reports).grid(row=0, column=4)

        body = ttk.PanedWindow(outer, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew")

        left = ttk.Frame(body, style="Panel.TFrame", padding=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        body.add(left, weight=1)

        ttk.Label(left, text="Asset Browser", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        filter_frame = ttk.Frame(left, style="Panel.TFrame")
        filter_frame.grid(row=1, column=0, sticky="ew", pady=(8, 10))
        filter_frame.columnconfigure(0, weight=1)
        filter_entry = ttk.Entry(filter_frame, textvariable=self.file_filter_var)
        filter_entry.grid(row=0, column=0, sticky="ew")
        filter_entry.bind("<KeyRelease>", lambda _event: self.apply_filter())

        self.file_list = tk.Listbox(left, activestyle="none", bg="#fbf7ef", fg="#2d2417", selectbackground="#b69e6a", selectforeground="#1f160a", font=("Consolas", 10), borderwidth=0, highlightthickness=0)
        self.file_list.grid(row=2, column=0, sticky="nsew")
        self.file_list.bind("<<ListboxSelect>>", lambda _event: self.on_select_file())

        right = ttk.Frame(body, style="Panel.TFrame", padding=10)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        body.add(right, weight=4)

        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.overview_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        self.atlas_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        self.map_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        self.records_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        self.parts_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        self.reports_frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=10)
        for frame in (self.overview_frame, self.atlas_frame, self.map_frame, self.records_frame, self.parts_frame, self.reports_frame):
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)

        self.notebook.add(self.overview_frame, text="Overview")
        self.notebook.add(self.atlas_frame, text="Atlas")
        self.notebook.add(self.map_frame, text="Map Preview")
        self.notebook.add(self.records_frame, text="Records")
        self.notebook.add(self.parts_frame, text="Parts")
        self.notebook.add(self.reports_frame, text="Reports")

        self.overview_text = tk.Text(self.overview_frame, wrap="word", bg="#fbf7ef", fg="#2d2417", font=("Consolas", 10), borderwidth=0, highlightthickness=0)
        self.overview_text.grid(row=0, column=0, sticky="nsew")

        atlas_toolbar = ttk.Frame(self.atlas_frame, style="Panel.TFrame")
        atlas_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(atlas_toolbar, text="Palette", style="Body.TLabel").pack(side="left")
        self.palette_combo = ttk.Combobox(atlas_toolbar, textvariable=self.palette_var, state="readonly", width=6)
        self.palette_combo.pack(side="left", padx=(8, 0))
        self.palette_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_document_views())
        self.atlas_view = ScrollableImage(self.atlas_frame)
        self.atlas_view.grid(row=1, column=0, sticky="nsew")
        self.atlas_frame.rowconfigure(1, weight=1)

        self.map_view = ScrollableImage(self.map_frame)
        self.map_view.grid(row=0, column=0, sticky="nsew")

        self.records_tree = ttk.Treeview(self.records_frame, columns=("index", "a", "a_hi", "b", "c", "refs", "part"), show="headings")
        for key, label, width in (
            ("index", "#", 60),
            ("a", "A.low16", 90),
            ("a_hi", "A.high16", 90),
            ("b", "B", 80),
            ("c", "C", 110),
            ("refs", "Map Refs", 90),
            ("part", "Part", 80),
        ):
            self.records_tree.heading(key, text=label)
            self.records_tree.column(key, width=width, anchor="center")
        self.records_tree.grid(row=0, column=0, sticky="nsew")

        self.parts_tree = ttk.Treeview(self.parts_frame, columns=("part", "rect", "size"), show="headings")
        for key, label, width in (
            ("part", "Part", 80),
            ("rect", "Pixel Rect", 220),
            ("size", "Size", 100),
        ):
            self.parts_tree.heading(key, text=label)
            self.parts_tree.column(key, width=width, anchor="center")
        self.parts_tree.grid(row=0, column=0, sticky="nsew")

        self.reports_text = tk.Text(self.reports_frame, wrap="word", bg="#fbf7ef", fg="#2d2417", font=("Consolas", 10), borderwidth=0, highlightthickness=0)
        self.reports_text.grid(row=0, column=0, sticky="nsew")

        status = ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", anchor="w", padding=(12, 6))
        status.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    def choose_game_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.game_dir_var.get() or str(Path.home()))
        if selected:
            self.game_dir_var.set(selected)

    def scan_game(self) -> None:
        game_dir = Path(self.game_dir_var.get()).expanduser()
        if not game_dir.exists():
            messagebox.showerror("Invalid directory", "The selected game directory does not exist.")
            return
        try:
            self.status_var.set("Scanning workspace...")
            self.root.update_idletasks()
            self.current_scan_debug, self.current_scan_groups = scan_workspace(game_dir)
            self.cell_files = list_cell_files(game_dir)
            self.apply_filter()
            self.populate_reports_panel()
            self.status_var.set(f"Scanned {len(self.cell_files)} Cell candidates.")
        except Exception as exc:
            messagebox.showerror("Scan failed", str(exc))
            self.status_var.set("Scan failed.")

    def write_reports(self) -> None:
        game_dir = Path(self.game_dir_var.get()).expanduser()
        if self.current_scan_debug is None or self.current_scan_groups is None:
            self.scan_game()
        if self.current_scan_debug is None or self.current_scan_groups is None:
            return
        out_dir = ROOT / "out"
        json_path = write_json_report(out_dir, self.current_scan_debug, self.current_scan_groups)
        md_path = write_markdown_report(out_dir, self.current_scan_debug, self.current_scan_groups)
        logic_path = write_logic_report(out_dir, self.current_scan_groups)
        self.populate_reports_panel()
        self.status_var.set(f"Reports written: {json_path.name}, {md_path.name}, {logic_path.name}")

    def apply_filter(self) -> None:
        needle = self.file_filter_var.get().strip().lower()
        self.filtered_files = [path for path in self.cell_files if needle in str(path).lower()] if needle else list(self.cell_files)
        self.file_list.delete(0, tk.END)
        base = Path(self.game_dir_var.get()).expanduser()
        for path in self.filtered_files:
            label = str(path.relative_to(base)) if base.exists() and base in path.parents else str(path)
            self.file_list.insert(tk.END, label)

    def on_select_file(self) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        path = self.filtered_files[selection[0]]
        try:
            self.status_var.set(f"Loading {path.name}...")
            self.root.update_idletasks()
            self.current_document = load_cell_document(path)
            self.refresh_document_views()
            self.status_var.set(f"Loaded {path.name}")
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            self.status_var.set("Load failed.")

    def refresh_document_views(self) -> None:
        if self.current_document is None:
            return
        palette_index = int(self.palette_var.get() or 0)
        palette_count = len(self.current_document.palettes) if self.current_document.palettes else (1 if self.current_document.texture and self.current_document.texture.storage_kind == "png" else 0)
        if palette_count > 0:
            self.palette_combo.configure(values=[str(index) for index in range(palette_count)])
            if self.palette_var.get() not in self.palette_combo.cget("values"):
                self.palette_var.set("0")
        else:
            self.palette_combo.configure(values=[])
            self.palette_var.set("0")

        self.current_atlas = build_atlas_for_document(self.current_document, palette_index)
        self.current_map_image = render_map_image(self.current_document, palette_index, max_edge=1400)
        self.atlas_view.set_image(self.current_atlas)
        self.map_view.set_image(self.current_map_image)
        self.populate_overview()
        self.populate_records()
        self.populate_parts()

    def populate_overview(self) -> None:
        document = self.current_document
        if document is None:
            return
        lines: list[str] = []
        lines.append(f"Source: {document.source_path}")
        lines.append(f"LZ77: {'yes' if document.lz77 else 'no'}")
        lines.append(f"Cell Header: table_offset=0x{document.header.table_offset:X}, entries={document.header.entry_count}, grid={document.header.grid_width}x{document.header.grid_height}")
        lines.append(f"Chunks: {', '.join(chunk.name for chunk in document.chunks)}")
        if document.cell_map is not None:
            lines.append(f"Map Grid: {document.cell_map.width}x{document.cell_map.height} ({len(document.cell_map.values)} cells)")
        if document.texture is not None:
            lines.append(
                f"Texture Atlas: {document.texture.header.width}x{document.texture.header.height}, "
                f"storage={document.texture.storage_kind}, parts={len(document.texture.parts)}, palettes={len(document.palettes)}"
            )
        lines.append("")
        lines.append("Interpretation")
        lines.append("- Map.low16 -> record index")
        lines.append("- record.value_a.low16 -> texture part index")
        lines.append("- Map.high16 / record.value_a.high16 likely carry flags or variants")
        lines.append("")
        lines.append("Debug Snapshot")
        if self.current_scan_debug is not None:
            for marker, found in self.current_scan_debug.markers_found.items():
                lines.append(f"- {marker}: {found}")
        self.overview_text.delete("1.0", tk.END)
        self.overview_text.insert("1.0", "\n".join(lines))

    def populate_records(self) -> None:
        document = self.current_document
        if document is None:
            return
        self.records_tree.delete(*self.records_tree.get_children())
        ref_counts: dict[int, int] = {}
        if document.cell_map is not None:
            for value in document.cell_map.values:
                record_index = value & 0xFFFF
                ref_counts[record_index] = ref_counts.get(record_index, 0) + 1
        for record in document.decoded_records:
            self.records_tree.insert(
                "",
                tk.END,
                values=(
                    record.index,
                    record.value_a_low16,
                    record.value_a_high16,
                    f"0x{record.value_b:08X}",
                    f"0x{record.value_c:08X}",
                    ref_counts.get(record.index, 0),
                    record.value_a_low16,
                ),
            )

    def populate_parts(self) -> None:
        document = self.current_document
        self.parts_tree.delete(*self.parts_tree.get_children())
        if document is None or document.texture is None:
            return
        for part in document.texture.parts:
            x0, y0, x1, y1 = part.pixel_rect(document.texture.header.width, document.texture.header.height)
            self.parts_tree.insert("", tk.END, values=(part.index, f"{x0},{y0} -> {x1},{y1}", f"{round(part.width)}x{round(part.height)}"))

    def populate_reports_panel(self) -> None:
        out_dir = ROOT / "out"
        sections: list[str] = []
        for name in ("map_logic_report.md", "scan_report.md"):
            path = out_dir / name
            if path.exists():
                sections.append(f"===== {name} =====")
                sections.append(path.read_text(encoding="utf-8"))
                sections.append("")
        self.reports_text.delete("1.0", tk.END)
        self.reports_text.insert("1.0", "\n".join(sections) if sections else "No reports written yet.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the Dokapon development tools UI.")
    parser.add_argument("--game-dir", type=Path, default=None, help="Game installation directory")
    args = parser.parse_args()

    root = tk.Tk()
    app = DevToolsApp(root, args.game_dir)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
