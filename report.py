import enum
import gzip
import glob
import base64
import time
import json
import typing as T
from collections import defaultdict
from functools import cached_property
import datetime

wrstat_reports = glob.glob(
    "/lustre/scratch114/teams/hgi/lustre_reports/wrstat/data/*_scratch114.*.*.stats.gz")
wrstat_reports.sort()

PROJECT_DIR = "/lustre/scratch114/projects/crohns"
DELETION_THRESHOLD = 90  # Days

FILETYPES = [".sam", ".vcf", ".py", ".bam", ".cram",
             ".bcf", ".fastq", ".fasta", ".txt", ".vcf.gz", ".R", ".bed", ".log"]


class KeepStatus(enum.Enum):
    Keep = enum.auto()
    Delete = enum.auto()
    Parent = enum.auto()


class Expiry(enum.Enum):
    Expired = enum.auto()
    InDate = enum.auto()
    Directory = enum.auto()


class FileNode:
    def __init__(self, expired: Expiry, size: int):
        self.children: T.Dict[str, FileNode] = {}
        self.expired: Expiry = expired
        self._fsize: int = size

    def add_child(self, path: str, expired: Expiry, size: int) -> None:
        path_parts = path.strip("/").split("/")
        if path_parts[0] == "":
            return

        if path_parts[0] not in self.children:
            # if the child doesn't exist - make it
            self.children[path_parts[0]] = FileNode(expired, size)

        if len(path_parts[1:]) > 0:
            # if there's further children - make them
            self.children[path_parts[0]].add_child(
                "/".join(path_parts[1:]), expired, size)

        else:
            # if there aren't further children, ensure the data is right,
            # as it may not be if it was made out of sequence
            self.children[path_parts[0]].expired = expired
            self.children[path_parts[0]]._fsize = size

    @cached_property
    def size(self) -> int:
        return self._fsize + \
            sum(x.size for x in self.children.values())

    @cached_property
    def keep(self) -> KeepStatus:
        if self.expired is not Expiry.Directory:
            # Files
            return KeepStatus.Delete if self.expired == Expiry.Expired else KeepStatus.Keep

        else:
            # Directories
            if all(x.keep == KeepStatus.Delete for x in self.children.values()):
                return KeepStatus.Delete
            elif all(x.keep == KeepStatus.Keep for x in self.children.values()):
                return KeepStatus.Keep
            else:
                return KeepStatus.Parent

    def prune(self) -> None:
        if self.keep != KeepStatus.Parent:
            self.children = {}
        else:
            for child in self.children.values():
                child.prune()

    @property
    def dict(self) -> T.Dict[str, T.Any]:
        return {
            "expired": self.expired.name,
            "size": self.size,
            "keep": self.keep.name,
            "children": {k: v.dict for (k, v) in self.children.items()}
        }

    def json(self) -> str:
        return json.dumps(self.dict)

    @cached_property
    def filetypes(self) -> T.DefaultDict[str, T.List[int]]:
        sizes: T.DefaultDict[str, T.List[int]] = defaultdict(lambda: [0, 0])
        for child, node in self.children.items():
            if len(node.children) == 0:
                if node.keep == KeepStatus.Delete:
                    for filetype in FILETYPES:
                        if child.endswith(filetype):
                            sizes[filetype] = [sizes[filetype][0] +
                                               1, sizes[filetype][1] + node.size]
            else:
                for filetype, details in node.filetypes.items():
                    sizes[filetype] = [sizes[filetype][0] +
                                       details[0], sizes[filetype][1] + details[1]]

        return sizes

    def __hash__(self) -> int:
        return hash((self.expired, self._fsize, *self.children.items()))


def main():
    root_node = FileNode(Expiry.Directory, 0)
    with gzip.open(wrstat_reports[-1], "rt") as f:
        for line in f:
            wr_info = line.split()
            path = base64.b64decode(wr_info[0]).decode("UTF-8", "replace")
            if path.startswith(PROJECT_DIR):
                if wr_info[7] == "f":
                    root_node.add_child(path, Expiry.Expired if int(wr_info[5]) < time.time(
                    ) - DELETION_THRESHOLD * 60*60*24 else Expiry.InDate, int(wr_info[1]))
                else:
                    root_node.add_child(
                        path, Expiry.Directory, int(wr_info[1]))

    # Ensure the top levels are all Expiry.Directory and KeepStatus.Parent
    for i in range(len(PROJECT_DIR.split("/"))):
        root_node.add_child("/".join(PROJECT_DIR.split("/")
                            [:i]), Expiry.Directory, 4096)

    root_node.size  # populate all the size fields pre-prune
    root_node.filetypes  # populates a filetypes dictionary pre-prune
    root_node.prune()

    to_delete: T.List[T.Tuple[str, int]] = []
    to_keep: T.List[T.Tuple[str, int]] = []

    def fill_to_delete(path: str, node: FileNode) -> None:
        if node.keep == KeepStatus.Delete:
            to_delete.append((path, node.size))
        elif node.keep == KeepStatus.Parent:
            for k, v in node.children.items():
                fill_to_delete(path + "/" + k, v)

    def fill_to_keep(path: str, node: FileNode) -> None:
        if node.keep == KeepStatus.Keep:
            to_keep.append((path, node.size))
        elif node.keep == KeepStatus.Parent:
            for k, v in node.children.items():
                fill_to_keep(path + "/" + k, v)

    fill_to_delete("", root_node)
    fill_to_keep("", root_node)

    class SizeUnit(enum.Enum):
        B = 1
        KiB = 2
        MiB = 3
        GiB = 4
        TiB = 5

    def human(size: int) -> str:
        for unit in SizeUnit:
            if size < 1024 ** unit.value:
                return f"{round(size / 1024**(unit.value-1), 1)}{unit.name}"
        return ">PiB"

    # Output in valid markdown
    print(
        f"# Report - {PROJECT_DIR} \n # Deletion Threshold: {DELETION_THRESHOLD} days \n # {datetime.datetime.now().strftime('%d/%m/%Y')}")

    print("## Filetypes\n<table><tr><th>Filetype</th><th>Num. of Files</th><th>Space</th></tr>")
    for row, details in root_node.filetypes.items():
        print(
            f"<tr><td>{row}</td><td>{details[0]}</td><td>{human(details[1])}</td></tr>")

    print("</table>\n\n## Will Be Deleted\n\n```")
    for p in to_delete:
        print(p[0], human(p[1]))
    print("```\n---\n## Won't Be Deleted\n```")
    for p in to_keep:
        print(p[0], human(p[1]))
    print("```\n---")


if __name__ == "__main__":
    main()
