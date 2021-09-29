import enum
import gzip
import glob
import base64
import time

wrstat_reports = glob.glob(
    "/lustre/scratch114/teams/hgi/lustre_reports/wrstat/data/*_scratch114.*.*.stats.gz")
wrstat_reports.sort()

PROJECT_DIR = "/lustre/scratch114/projects/crohns"
DELETION_THRESHOLD = 90  # Days


class KeepStatus(enum.Enum):
    Keep = enum.auto()
    Delete = enum.auto()
    Parent = enum.auto()


class FileNode:
    def __init__(self, expired, size):
        self.children = {}
        self.expired = expired
        self._fsize = size

        self._size = None
        self._keep = None

    def add_child(self, path: str, last_mod, size):
        if path.strip("/").split("/")[0] == "":
            return
        if path.split("/")[0] in self.children:
            self.children[path.split(
                "/")[0]].add_child("/".join(path.split("/")[1:]), last_mod, size)
        else:
            self.children[path.split("/")[0]] = FileNode(last_mod, size)

    @property
    def size(self):
        if self._size is None:
            self._size = self._fsize + \
                sum(x.size for x in self.children.values())
        return self._size

    @property
    def keep(self):
        if self._keep is None:
            if self.expired is not None:
                # Files
                self.keep = KeepStatus.Delete if self.expired else KeepStatus.Keep

            else:
                # Directories
                if all(x.keep == KeepStatus.Delete for x in self.children.values()):
                    self.keep = KeepStatus.Delete
                elif all(x.keep == KeepStatus.Keep for x in self.children.values()):
                    self.keep = KeepStatus.Keep
                else:
                    self.keep = KeepStatus.Parent

        return self._keep

    def prune(self):
        if self.keep != KeepStatus.Parent:
            self.children = {}
        else:
            for child in self.children.values():
                child.prune()


root_node = FileNode(False, 0)
with gzip.open(wrstat_reports[-1]) as f:
    for line in f:
        wr_info = line.split()
        path = base64.b64decode(wr_info[0]).decode("UTF-8", "replace")
        if path.startswith(PROJECT_DIR):
            if wr_info[7] == "f":
                root_node.add_child(path, int(wr_info[5]) < time.time(
                ) - DELETION_THRESHOLD * 60*60*24, int(wr_info[1]))
            else:
                root_node.add_child(path, None, int(wr_info[1]))

root_node.size  # populate all the size fields
root_node.prune()

to_delete = []
to_keep = []


def fill_to_delete(path, node):
    if node.keep:
        for k, v in node.children.items():
            fill_to_delete(path + "/" + k, v)
    else:
        to_delete.append((path[1:], node.size))


def fill_to_keep(path, node):
    if node.keep:
        if len(node.children) == 0:
            to_keep.append((path[1:], node.size))
        else:
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
