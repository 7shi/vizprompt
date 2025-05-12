import sys, os, uuid
from datetime import datetime
from ruamel.yaml import YAML
from vizprompt.core.base import BaseManager

yaml = YAML()
yaml.default_flow_style = False
yaml.allow_unicode = True

class Flow:
    def __init__(self, id, name, created, updated, description, connections, data_dir, relpath):
        self.id = id
        self.name = name
        self.created = created
        self.updated = updated
        self.description = description
        self.data_dir = data_dir
        self.relpath = relpath

        # 有向グラフに変換（双方向）
        self.connections = [] # (from_id, to_id) のリスト
        self.graph_fwd = {}
        self.graph_rev = {}
        for from_id, to_id in connections:
            try:
                self.connect(from_id, to_id)
            except Exception as e:
                print(e, file=sys.stderr)

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
        path = os.path.join(self.data_dir, self.relpath)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)

    @classmethod
    def load(cls, data_dir, relpath):
        path = os.path.join(data_dir, relpath)
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
            data_dir=data_dir,
            relpath=relpath,
        )

    def update(self):
        self.updated = datetime.now().astimezone()

    def connect(self, from_id, to_id):
        if (from_id, to_id) not in self.connections:
            if self.would_create_cycle(from_id, to_id):
                raise Exception("循環が検出されました")
            self.connections.append((from_id, to_id))
            self.graph_fwd.setdefault(from_id, []).append(to_id)
            self.graph_rev.setdefault(to_id, []).append(from_id)
        self.update()

    def would_create_cycle(self, from_id, to_id):
        """
        (from_id, to_id) を追加した場合に循環が発生するか判定（DFS）
        """
        # 確認用にコピーして仮接続
        graph = self.graph_fwd.copy()
        graph.setdefault(from_id, []).append(to_id)

        # DFSで循環を検出
        stack = [to_id]
        visited = set() # 訪れたノードを記録
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            if current == from_id:
                # 循環を検出
                return True
            visited.add(current)
            stack.extend(graph.get(current, []))

        # 循環が検出されなかった
        return False

    def _rebuild_graph(self):
        """
        グラフを再構築する（接続が変更された場合に呼び出す）
        """
        self.graph_fwd = {}
        self.graph_rev = {}
        for from_id, to_id in self.connections:
            self.graph_fwd.setdefault(from_id, []).append(to_id)
            self.graph_rev.setdefault(to_id, []).append(from_id)

    def disconnect(self, from_id, to_id):
        if (from_id, to_id) in self.connections:
            self.connections.remove((from_id, to_id))
            self._rebuild_graph()
        self.update()

    def remove_node(self, node_id):
        for conn in list(self.connections):
            if node_id in conn:
                self.connections.remove(conn)
        self._rebuild_graph()
        self.update()

    def get_history(self, node_id):
        """
        指定したノード以前の履歴を取得
        """
        if node_id not in self.graph_rev:
            return []

        # 開始ノードから到達出来るノードを深さ優先で探索
        visited = set()
        stack = [node_id]
        while stack:
            n = stack.pop()
            if n not in visited:
                visited.add(n)
                stack.extend(self.graph_rev.get(n, []))

        # 各ノードの入次数を数える
        # 今回通るルートに限定するため、graph_fwdの個数とは異なる
        in_degree = {n: 0 for n in visited}
        for n in visited:
            for m in self.graph_rev.get(n, []):
                if m in visited:
                    in_degree[m] += 1

        # Kahn 法 (LIFO)
        history = []
        stack = [node_id]
        while stack:
            n = stack.pop()
            history.insert(0, n)
            for m in self.graph_rev.get(n, []):
                in_degree[m] -= 1
                # すべての合流が解消すれば先に進む（分岐のjoin）
                if in_degree[m] == 0:
                    stack.append(m)

        return history

    def get_histories(self):
        """
        すべての履歴を取得
        """
        if not self.connections:
            return []

        histories = []

        fwd = set(self.graph_fwd.keys())
        rev = set(self.graph_rev.keys())

        nodes = fwd | rev  # すべてのノード
        terms = rev - fwd  # 終端ノード

        # 終端ノードからたどれるノードをnodesから除去
        for n in terms:
            history = self.get_history(n)
            histories.append(history)
            nodes -= set(history)

        # nodesに残っているのは循環したノード（原則的にないはず）
        if nodes:
            print(f"循環ノード: {nodes}", file=sys.stderr)

        return histories

class FlowManager(BaseManager):
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
            flow = Flow.load(self.data_dir, relpath)
            self.cache[flow_id] = flow
            return flow
        raise FileNotFoundError(f"Flow with ID {flow_id} not found.")

    def create_flow(self, name, description=""):
        relpath = self.get_next_relpath_and_folder()

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
            data_dir=self.data_dir,
            relpath=relpath,
        )
        flow.save()

        # キャッシュ・TSV追記
        self.cache[flow_id] = flow
        self.add_entry(relpath, flow_id, timestamp)
        self.append_index(relpath, flow_id, timestamp)

        return flow
