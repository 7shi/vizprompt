import sys, os, uuid
from datetime import datetime
from ruamel.yaml import YAML
from vizprompt.core.base import BaseManager

yaml = YAML()
yaml.default_flow_style = False
yaml.allow_unicode = True

class Flow:
    def __init__(self, id, name, created, updated, description, nodes, connections, data_dir, relpath):
        self.id = id
        self.name = name
        self.created = created
        self.updated = updated
        self.description = description
        self.data_dir = data_dir
        self.relpath = relpath
        self.nodes = nodes
        self.node_index = self._node_index()

        # 有向グラフに変換（双方向）
        self.connections = [] # (from_id, to_id) のリスト
        self.graph_fwd = {}
        self.graph_rev = {}
        for from_id, to_id in connections:
            try:
                self.connect(from_id, to_id)
            except Exception as e:
                print(e, file=sys.stderr)

    def _node_index(self):
        return {n: i for i, n in enumerate(self.nodes, 1)}

    def to_dict(self):
        nodes = [{"index": i, "id": node_id} for i, node_id in enumerate(self.nodes, 1)]
        connections = []
        for (from_id, to_id) in self.connections:
            from_index = self.node_index.get(from_id)
            to_index   = self.node_index.get(to_id)
            if from_index is not None and to_index is not None:
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

        nodes = []
        index_to_id = {}
        for node_id in data.get("nodes", []):
            nodes.append(node_id["id"])
            index_to_id[node_id["index"]] = node_id["id"]
        connections = [
            (index_to_id[f], index_to_id[t])
            for conn in data.get("connections", [])
            if (f := conn["from"]) in index_to_id and (t := conn["to"]) in index_to_id
        ]

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            created=datetime.fromisoformat(data["created"]),
            updated=datetime.fromisoformat(data["updated"]),
            description=data.get("description", ""),
            nodes=nodes,
            connections=connections,
            data_dir=data_dir,
            relpath=relpath,
        )

    def update(self):
        self.updated = datetime.now().astimezone()

    def connect(self, from_id, to_id):
        if from_id and from_id not in self.nodes:
            self.nodes.append(from_id)
            self.node_index[from_id] = len(self.nodes)
        if to_id and to_id not in self.nodes:
            self.nodes.append(to_id)
            self.node_index[to_id] = len(self.nodes)
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
        graph = {k: v.copy() for k, v in self.graph_fwd.items()}
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
        self.connections = []
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
        if node_id in self.nodes:
            self.nodes.remove(node_id)
            self.node_index = self._node_index()
        self._rebuild_graph()
        self.update()

    def get_previous(self, node_id):
        """
        指定したノードの前のノードを取得
        """
        return self.graph_rev.get(node_id, [])

    def get_in_degree_map(self, nodes: set[str]) -> dict[str, int]:
        """
        指定した部分グラフにおけるノードの入次数を取得
        """
        # ルートを限定するため、graph_fwdの個数とは異なる
        in_degree = {n: 0 for n in nodes}
        for n in nodes:
            for m in self.graph_fwd.get(n, []):
                if m in nodes:
                    in_degree[m] += 1
        return in_degree

    def build_history_by_kahn_lifo(self, in_degree: dict[str, int]) -> list[str]:
        """
        Kahn 法 (LIFO) を用いて履歴を構築する
        """
        history = []
        starts = [n for n in self.nodes if in_degree.get(n, -1) == 0]
        for node_id in starts:
            stack = [node_id]
            while stack:
                n = stack.pop()
                history.append(n)
                for m in reversed(self.graph_fwd.get(n, [])):
                    in_degree[m] -= 1
                    # すべての合流が解消すれば先に進む（分岐のjoin）
                    if in_degree[m] == 0:
                        stack.append(m)
        return history

    def get_history(self, node_id: str) -> list[str]:
        """
        指定したノード以前の履歴を取得
        """
        if node_id not in self.nodes:
            return []

        # 開始ノードから到達出来るノードを深さ優先で探索
        visited = set()
        stack = [node_id]
        while stack:
            n = stack.pop()
            if n not in visited:
                visited.add(n)
                stack.extend(self.graph_rev.get(n, []))

        in_degree = self.get_in_degree_map(visited)
        return self.build_history_by_kahn_lifo(in_degree)

    @staticmethod
    def merge_overlapping_sets(list_of_sets: list[set[str]]) -> list[set[str]]:
        """
        setのlistを渡して、setに重複があれば統合したlistを返す
        """
        merged = []
        for s in list_of_sets:
            s = s.copy()
            found = []
            for m in merged:
                if s & m:
                    found.append(m)
            if found:
                # すべての重複集合を統合
                for m in found:
                    s |= m
                    merged.remove(m)
            merged.append(s)
        return merged

    def get_histories(self):
        """
        すべての履歴を取得
        """
        # 開始ノードを取得
        starts = [n for n in self.nodes if n not in self.graph_rev]

        # 開始ノードから到達できるノードを深さ優先探索で取得
        visited = set()
        routes = []
        for start in starts:
            route = set()
            stack = [start]
            while stack:
                n = stack.pop()
                if n not in route:
                    route.add(n)
                    if n not in visited:
                        stack.extend(self.graph_fwd.get(n, []))
            routes.append(route)
            visited.update(route)

        # 重複を統合
        merged = self.merge_overlapping_sets(routes)

        # 循環したノードをチェック（原則的にないはず）
        left_nodes = set(self.nodes) - set().union(*merged)
        if left_nodes:
            print("循環ノード:", left_nodes, file=sys.stderr)

        # 履歴に変換
        histories = []
        for s in merged:
            in_degree = self.get_in_degree_map(s)
            history = self.build_history_by_kahn_lifo(in_degree)
            histories.append(history)
        return histories

    def convert_map(self, history: list[str]) -> list[str]:
        """
        `history`は`get_history`で取得した履歴
        履歴を分岐・合流でネストしたテキスト形式に変換
        ノードは出現順に1,2,3,...と連番を振る
        分岐点（out-degree>1）で"<"、合流点（in-degree>1）で">"を付ける
        2行目以降はスペース2つでインデント（ネストは数えない）
        """
        # 入次数・出次数を取得
        fwd = {str(self.node_index[n]): [] for n in history}
        rev = {k: [] for k in fwd}
        for n in history:
            ni = str(self.node_index[n])
            for m in self.graph_fwd.get(n, []):
                if m in history:
                    mi = str(self.node_index[m])
                    # n (fwd) → m (rev)
                    fwd[ni].append(mi)
                    rev[mi].append(ni)

        # 履歴を分岐・合流でネストしたテキスト形式に変換
        lines = []
        line = ""
        prev = None # 直前のノード
        for n in history:
            i = str(self.node_index[n])
            if prev:
                if prev not in rev[n]:
                    outs = ",".join(fwd[prev])
                    if outs:
                        line += f">{outs}"
                    lines.append(line)
                    line = "  "
                    ins = ",".join(rev[n])
                    if ins:
                        line += f"{ins}<"
                elif len(rev[n]) > 1: # 合流点
                    lines.append(f"{line}>{i}")
                    line = "  >"
                elif len(fwd[prev]) > 1: # 直前で分岐
                    pass
                else: # 連続的な推移
                    line += "→"
            line += i
            if len(fwd[i]) > 1: # 分岐点
                lines.append(f"{line}<")
                line = f"  {i}<"
            prev = n
        lines.append(line)

        return lines

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
            nodes=[],
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
