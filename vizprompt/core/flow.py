import os, uuid
from datetime import datetime
from ruamel.yaml import YAML
from vizprompt.core.base import UUIDTimestampManager

yaml = YAML()
yaml.default_flow_style = False
yaml.allow_unicode = True

class Flow:
    def __init__(self, id, name, created, updated, description, connections, path):
        self.id = id
        self.name = name
        self.created = created
        self.updated = updated
        self.description = description
        self.connections = connections # (from_id, to_id) のリスト
        self.path = path

    def to_dict(self):
        nodes = []
        connections = []
        uuid_to_index = {}

        def id_to_index(id):
            if id in uuid_to_index:
                return uuid_to_index[id]
            index = len(uuid_to_index) + 1
            uuid_to_index[id] = index
            nodes.append({"index": index, "id": id})
            return index

        for (from_id, to_id) in self.connections:
            from_index = id_to_index(from_id)
            to_index = id_to_index(to_id)
            connections.append({
                "from": from_index,
                "to": to_index
            })

        return {
            "id": self.id,
            "name": self.name,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "description": self.description,
            "nodes": nodes,
            "connections": connections,
        }

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        nodes = {node["index"]: node["id"] for node in data.get("nodes", [])}
        connections = [
            (nodes[conn["from"]], nodes[conn["to"]])
            for conn in data.get("connections", [])
        ]

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            created=datetime.fromisoformat(data["created"]),
            updated=datetime.fromisoformat(data["updated"]),
            description=data.get("description", ""),
            connections=connections,
            path=path,
        )

    def update(self):
        self.updated = datetime.now().astimezone()

    def connect(self, from_id, to_id):
        if (from_id, to_id) not in self.connections:
            self.connections.append((from_id, to_id))
        self.update()

    def disconnect(self, from_id, to_id):
        if (from_id, to_id) in self.connections:
            self.connections.remove((from_id, to_id))
        self.update()

    def remove_node(self, node_id):
        self.connections = [conn for conn in self.connections if node_id not in conn]
        self.update()

    def get_previous(self, flow_id):
        """
        直前のノードをべて取得
        """
        flows = []
        for from_id, to_id in self.connections:
            if to_id == flow_id:
                flows.append(from_id)
        return flows

    def exists(self, flow_id):
        """
        ノードが存在するか確認
        """
        return any(flow_id in conn for conn in self.connections)

    def get_history(self, flow_id):
        """
        履歴を取得
        """
        if not self.exists(flow_id):
            return []
        flows = [flow_id]

        def f(id):
            for from_id in self.get_previous(id):
                # 循環を避けるため、すでに訪れたノードはスキップ
                if from_id in flows:
                    continue
                flows.insert(0, from_id)
                f(from_id)

        f(flow_id)
        return flows

class FlowManager(UUIDTimestampManager):
    def __init__(self, base_dir="project"):
        self.base_dir = base_dir
        self.cache = {}
        super().__init__(
            data_dir=os.path.join(base_dir, "flows"),
            ext="yaml",
        )

    def get_uuid_and_timestamp_from_file(self, path):
        try:
            id, updated = None, None
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("id:"):
                        id = line.split(":")[1].strip()
                    elif line.startswith("updated:"):
                        updated = line.split(":")[1].strip()
                    if id and updated:
                        return id, datetime.fromisoformat(updated)
        except Exception:
            pass
        # 取得できなかった場合はゼロUUIDと現在のタイムスタンプを返す
        return str(uuid.UUID(int=0)), datetime.now().astimezone()

    def get_flow(self, flow_id):
        """
        UUIDからFlowインスタンスを取得
        """
        if flow := self.cache.get(flow_id):
            # キャッシュにある場合はキャッシュから取得
            return flow
        if flow_id in self.uuid_map:
            # キャッシュにない場合はファイルから読み込む
            relpath = self.uuid_map[flow_id][0]
            path = os.path.join(self.data_dir, relpath)
            flow = Flow.load(path)
            self.cache[flow_id] = flow
            return flow
        raise FileNotFoundError(f"Flow with ID {flow_id} not found.")

    def create_flow(self, name, description=""):
        relpath = self.get_next_relpath_and_folder()
        path = os.path.join(self.data_dir, relpath)

        # 新規作成
        flow_id = self.generate_uuid()
        timestamp = datetime.now().astimezone()
        flow = Flow(
            id=flow_id,
            name=name,
            created=timestamp,
            updated=timestamp,
            description=description,
            connections=[],
            path=path,
        )
        flow.save()

        # キャッシュ・TSV追記
        self.cache[flow_id] = flow
        self.add_entry(relpath, flow_id, timestamp)
        self.append_index(relpath, flow_id, timestamp)

        return flow
