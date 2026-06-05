"""Project state and persistence helpers for the Projects feature."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import re


def sanitize_project_name(name: str) -> str:
    """Return a filesystem-safe project name."""
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", (name or "").strip())
    cleaned = cleaned.strip(" ._")
    return cleaned or "Project"


def build_project_paths(root_dir: Path, project_name: str) -> Tuple[Path, Path, Path]:
    """Build the expected root, data, and project file paths."""
    project_root = Path(root_dir) / sanitize_project_name(project_name)
    data_dir = project_root / "Data"
    project_file = project_root / f"{sanitize_project_name(project_name)}.prj"
    return project_root, data_dir, project_file


@dataclass
class FigureSpec:
    """Serializable figure definition stored in a project file."""

    papers_included: List[str] = field(default_factory=list)
    x_variable: str = ""
    y_variable: str = ""
    z_variable: str = ""
    plot_representation: str = "2d_scatter"
    binning_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FigureSpec":
        return cls(
            papers_included=list(data.get("papers_included", [])),
            x_variable=str(data.get("x_variable", "")),
            y_variable=str(data.get("y_variable", "")),
            z_variable=str(data.get("z_variable", "")),
            plot_representation=str(data.get("plot_representation", "2d_scatter")),
            binning_data=dict(data.get("binning_data", {})),
        )


@dataclass
class ProjectState:
    """In-memory representation of the current project."""

    name: str = ""
    root_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    project_file: Optional[Path] = None
    data_frame: Any = None
    selected_papers: List[str] = field(default_factory=list)
    available_papers: List[str] = field(default_factory=list)
    figures: List[FigureSpec] = field(default_factory=list)
    dirty: bool = False

    @classmethod
    def blank(cls) -> "ProjectState":
        return cls()

    def is_loaded(self) -> bool:
        return self.root_dir is not None and self.data_dir is not None

    def next_paper_name(self) -> str:
        """Return the next sequential paper folder name."""
        if not self.data_dir or not self.data_dir.exists():
            return "P001"

        pattern = re.compile(r"^P(\d+)$", re.IGNORECASE)
        highest = 0

        for child in self.data_dir.iterdir():
            if not child.is_dir():
                continue

            match = pattern.match(child.name)
            if match:
                highest = max(highest, int(match.group(1)))

        return f"P{highest + 1:03d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root_dir": str(self.root_dir) if self.root_dir else "",
            "data_dir": str(self.data_dir) if self.data_dir else "",
            "project_file": str(self.project_file) if self.project_file else "",
            "selected_papers": list(self.selected_papers),
            "available_papers": list(self.available_papers),
            "figures": [figure.to_dict() for figure in self.figures],
            "dirty": self.dirty,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], project_file: Optional[Path] = None) -> "ProjectState":
        root_dir = Path(data["root_dir"]) if data.get("root_dir") else None
        data_dir = Path(data["data_dir"]) if data.get("data_dir") else None
        if project_file is not None:
            project_file_path = Path(project_file)
        else:
            project_file_path = Path(data["project_file"]) if data.get("project_file") else None

        return cls(
            name=str(data.get("name", "")),
            root_dir=root_dir,
            data_dir=data_dir,
            project_file=project_file_path,
            selected_papers=list(data.get("selected_papers", [])),
            available_papers=list(data.get("available_papers", [])),
            figures=[FigureSpec.from_dict(item) for item in data.get("figures", [])],
            dirty=bool(data.get("dirty", False)),
        )


def save_project_file(project: ProjectState) -> Path:
    """Persist the project state to its .prj file."""
    if not project.project_file:
        raise ValueError("Project file path is not set")

    payload = project.to_dict()
    project.project_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return project.project_file


def load_project_file(project_file: Path) -> ProjectState:
    """Load project state from a .prj file."""
    project_file = Path(project_file)
    payload = json.loads(project_file.read_text(encoding="utf-8"))
    return ProjectState.from_dict(payload, project_file=project_file)