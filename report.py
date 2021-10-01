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


class FiletypeInfo:
    def __init__(self):
        self.num_files: int = 0
        self.size: int = 0

    def update(self, num: int, size: int):
        self.num_files += num
        self.size += size


class FileNode:
    def __init__(self, expired: Expiry, size: int, owner: T.Optional[str]):
        self.children: T.Dict[str, FileNode] = {}
        self.expired: Expiry = expired
        self._fsize: int = size
        self.owner: T.Optional[str] = owner

    def add_child(self, path: str, expired: Expiry, size: int, owner: T.Optional[str]) -> None:
        path_parts = path.strip("/").split("/")
        if path_parts[0] == "":
            return

        if path_parts[0] not in self.children:
            # if the child doesn't exist - make it
            self.children[path_parts[0]] = FileNode(expired, size, owner)

        if len(path_parts[1:]) > 0:
            # if there's further children - make them
            self.children[path_parts[0]].add_child(
                "/".join(path_parts[1:]), expired, size, owner)

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
    def filetypes(self) -> T.DefaultDict[str, T.DefaultDict[str, FiletypeInfo]]:
        sizes: T.DefaultDict[str, T.DefaultDict[str, FiletypeInfo]] = defaultdict(
            lambda: defaultdict(FiletypeInfo))
        for child, node in self.children.items():
            if len(node.children) == 0 and node.owner:
                if node.keep == KeepStatus.Delete:
                    for filetype in FILETYPES:
                        if child.endswith(filetype):
                            sizes[node.owner][filetype].update(1, node.size)
                            break
                    else:
                        sizes[node.owner]["Other"].update(1, node.size)
            else:
                for owner, filetypes in node.filetypes.items():
                    for filetype, details in filetypes.items():
                        sizes[owner][filetype].update(
                            details.num_files, details.size)

        return sizes

    def __hash__(self) -> int:
        return hash((self.expired, self._fsize, *self.children.items()))


def fill_array_of_files(path: str, node: FileNode, keep_status: KeepStatus) -> T.List[T.Tuple[str, int]]:
    files: T.List[T.Tuple[str, int]] = []
    if node.keep == keep_status:
        files.append((path, node.size))
    elif node.keep == KeepStatus.Parent:
        for k, v in node.children.items():
            files.extend(fill_array_of_files(
                path + "/" + k, v, keep_status))
    return files


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


def main():
    root_node = FileNode(Expiry.Directory, 0, "")
    with gzip.open(wrstat_reports[-1], "rt") as f:
        for line in f:
            wr_info = line.split()
            path = base64.b64decode(wr_info[0]).decode("UTF-8", "replace")
            if path.startswith(PROJECT_DIR):
                if wr_info[7] == "f":
                    root_node.add_child(path, Expiry.Expired if int(wr_info[5]) < time.time(
                    ) - DELETION_THRESHOLD * 60*60*24 else Expiry.InDate, int(wr_info[1]), wr_info[2])
                else:
                    root_node.add_child(
                        path, Expiry.Directory, int(wr_info[1]), None)

    # Ensure the top levels are all Expiry.Directory and KeepStatus.Parent
    for i in range(len(PROJECT_DIR.split("/"))):
        root_node.add_child("/".join(PROJECT_DIR.split("/")
                            [:i]), Expiry.Directory, 4096, None)

    root_node.size  # populate all the size fields pre-prune
    root_node.filetypes  # populates a filetypes dictionary pre-prune
    root_node.prune()

    to_delete: T.List[T.Tuple[str, int]] = fill_array_of_files(
        "", root_node, KeepStatus.Delete)
    to_keep: T.List[T.Tuple[str, int]] = fill_array_of_files(
        "", root_node, KeepStatus.Keep)

    def _print_filetypes_table(filetypes: T.DefaultDict[str, FiletypeInfo]) -> None:
        print("<table><tr><th>Filetype</th><th>Num. of Files</th><th>Space</th></tr>")
        for row, details in filetypes.items():
            print(
                f"<tr><td>{row}</td><td>{details.num_files}</td><td>{details.size}</td></tr")
        print("</table>")

    # Output in valid markdown
    print(f"# Report - {PROJECT_DIR}")
    # yes, there's an extra new line
    print(f"**Deletion Threshold: {DELETION_THRESHOLD} days**\n")
    print(datetime.datetime.now().strftime('%d/%m/%Y'))

    print("## Filetypes")
    for user, user_filetypes in root_node.filetypes.items():
        print(f"### {user}")
        _print_filetypes_table(user_filetypes)

    print("## Will Be Deleted")
    print("```")
    for p in to_delete:
        print(p[0], human(p[1]))
    print("```\n---")

    print("## Won't Be Deleted")
    print("```")
    for p in to_keep:
        print(p[0], human(p[1]))
    print("```\n---")


if __name__ == "__main__":
    main()
