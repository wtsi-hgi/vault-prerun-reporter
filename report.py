import enum
import gzip
import glob
import base64
import time
import json

wrstat_reports = glob.glob(
    "/lustre/scratch114/teams/hgi/lustre_reports/wrstat/data/*_scratch114.*.*.stats.gz")
wrstat_reports.sort()

PROJECT_DIR = "/lustre/scratch114/projects/crohns"
DELETION_THRESHOLD = 90  # Days


class KeepStatus(enum.Enum):
    Keep = enum.auto()
    Delete = enum.auto()
    Parent = enum.auto()


class Expiry(enum.Enum):
    Expired = enum.auto()
    InDate = enum.auto()
    Directory = enum.auto()


class FileNode:
    def __init__(self, expired, size):
        self.children = {}
        self.expired = expired
        self._fsize = size

        self._size = None
        self._keep = None

    def add_child(self, path: str, expired, size):
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
            self.children[path.split("/")[0]].expired = expired
            self.children[path.split("/")[0]]._fsize = size

    @property
    def size(self):
        if self._size is None:
            self._size = self._fsize + \
                sum(x.size for x in self.children.values())
        return self._size

    @property
    def keep(self):
        if self._keep is None:
            if self.expired is not Expiry.Directory:
                # Files
                self._keep = KeepStatus.Delete if self.expired == Expiry.Expired else KeepStatus.Keep

            else:
                # Directories
                if all(x.keep == KeepStatus.Delete for x in self.children.values()):
                    self._keep = KeepStatus.Delete
                elif all(x.keep == KeepStatus.Keep for x in self.children.values()):
                    self._keep = KeepStatus.Keep
                else:
                    self._keep = KeepStatus.Parent

        return self._keep

    def prune(self):
        if self.keep != KeepStatus.Parent:
            self.children = {}
        else:
            for child in self.children.values():
                child.prune()

    @property
    def __dict__(self):
        return {"expired": self.expired.name, "size": self.size, "keep": self.keep.name, "children": {k: v.__dict for (k, v) in self.children.items()}}

    def json(self):
        return json.dumps(self.__dict__)


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
                root_node.add_child(path, Expiry.Directory, int(wr_info[1]))

# Ensure the top levels are all Expiry.Directory and KeepStatus.Parent
for i in range(len(PROJECT_DIR.split("/"))):
    root_node.add_child("/".join(PROJECT_DIR.split("/")
                        [:i]), Expiry.Directory, 4096)

root_node.size  # populate all the size fields
root_node.prune()

to_delete = []
to_keep = []


def fill_to_delete(path, node):
    if node.keep == KeepStatus.Delete:
        to_delete.append((path[1:], node.size))
    elif node.keep == KeepStatus.Parent:
        for k, v in node.children.items():
            fill_to_delete(path + "/" + k, v)


def fill_to_keep(path, node):
    if node.keep == KeepStatus.Keep:
        to_keep.append((path[1:], node.size))
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


def human(size):
    for unit in SizeUnit:
        if size < 1024 ** unit.value:
            return f"{round(size / 1024**(unit.value-1), 1)}{unit.name}"
    return ">PiB"


# Output in valid markdown
print(
    f"# Report {PROJECT_DIR} - Deletion Threshold: {DELETION_THRESHOLD} days")
print("## Will Be Deleted\n```")
for p in to_delete:
    print(p[0], human(p[1]))
print("```\n---\n## Won't Be Deleted\n```")
for p in to_keep:
    print(p[0], human(p[1]))
print("```\n---")
