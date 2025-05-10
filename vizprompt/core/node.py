import os, uuid
from datetime import datetime

import xml.etree.ElementTree as ET
from xml.dom.minidom import Document

def json_to_xml(json_obj):
    """
    JSONオブジェクトをXML形式に変換する関数
    """
    doc = Document()

    def build_xml_element(parent, key, value):
        if key is None:
            if not isinstance(value, dict) or len(value) != 1:
                raise ValueError(f"1要素の辞書でなければなりません: {value}")
            build_xml_element(parent, *list(value.items())[0])
        elif isinstance(value, dict):
            element = doc.createElement(key)
            parent.appendChild(element)
            for k, v in value.items():
                build_xml_element(element, k, v)
        elif isinstance(value, list):
            element = doc.createElement(key)
            parent.appendChild(element)
            for item in value:
                build_xml_element(element, None, item)
        else:
            v = str(value)
            if key == ":text":
                if v:
                    parent.appendChild(doc.createTextNode(v))
            elif key == ":cdata":
                if v:
                    parent.appendChild(doc.createCDATASection(f"\n{v}\n"))
            else:
                parent.setAttribute(key, v)

    build_xml_element(doc, None, json_obj)
    return doc

def _get_uuid_and_timestamp_from_xml(path):
    """
    XMLファイルのルート要素id属性とtimestamp属性を取得（なければゼロUUIDと現在のタイムスタンプを返す）
    """
    try:
        for _, elem in ET.iterparse(path, events=("start",)):
            if elem.tag == "node":
                if uuid_str := elem.attrib.get("id", None):
                    if timestamp := elem.attrib.get("timestamp", None):
                        return uuid_str, datetime.fromisoformat(timestamp)
                break
            else:
                break
    except Exception:
        pass
    return str(uuid.UUID(int=0)), datetime.now().astimezone()

class Node:
    """
    XMLノード情報と一対一対応するデータクラス
    """
    def __init__(
        self,
        *, # 引数名を指定して渡す
        id: str,
        timestamp: datetime,
        contents: list[dict],
        model: str,
        summary: str,
        summary_updated: bool,
        summary_last_built: datetime,
        tags: list,
        path: str,
    ):
        self.id = id
        self.timestamp = timestamp
        self.contents = contents
        self.model = model
        self.summary = summary
        self.summary_updated = summary_updated
        self.summary_last_built = summary_last_built
        self.tags = tags
        self.path = path

    def to_xml(self) -> str:
        """
        NodeインスタンスをXML文字列に変換
        """
        doc = json_to_xml(self.to_dict())
        return doc.toprettyxml(encoding='utf-8', indent='').decode('utf-8')

    def to_dict(self) -> dict:
        """
        NodeインスタンスのXML構造を辞書で返す
        """
        return {
            "node": {
                "id": self.id,
                "timestamp": self.timestamp.isoformat(),
                "contents": [
                    {
                        "content": {
                            "role": c["role"],
                            "count": c.get("count", 0),
                            "duration": float(f'{c.get("duration", 0):.2f}'),
                            "rate": float(f'{(c.get("count", 0) / c.get("duration", 0)):.2f}' if c.get("duration", 0) > 0 else 0),
                            ":cdata": c.get("text", ""),
                        }
                    }
                    for c in self.contents
                ],
                "metadata": {
                    "model": {
                        ":text": self.model,
                    },
                    "summary": {
                        "updated": str(self.summary_updated).lower(),
                        "last_built": self.summary_last_built.isoformat(),
                        ":cdata": self.summary if self.summary else "",
                    },
                    "tags": [
                        {"tag": tag} for tag in self.tags
                    ],
                },
            }
        }

    def save(self):
        """
        NodeインスタンスをXMLファイルに保存
        """
        xml = self.to_xml()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(xml)

class NodeManager:
    def __init__(self, base_dir="project"):
        self.base_dir = base_dir
        self.nodes_dir = os.path.join(base_dir, "nodes")
        self.map_path = os.path.join(base_dir, "metadata", "node_map.tsv")
        os.makedirs(self.nodes_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.map_path), exist_ok=True)
        self.tsv_entries = {}  # relpath -> (uuid, timestamp)
        self.uuid_map = {}     # uuid -> [relpath]
        self._check_and_update_node_map()

    def add_node(self, relpath, uuid, timestamp):
        """
        ノードを追加するメソッド
        relpath: ノードの相対パス
        uuid: ノードのUUID
        timestamp: ノードのタイムスタンプ
        """
        self.tsv_entries[relpath] = (uuid, timestamp)
        lst = self.uuid_map.setdefault(uuid, [])
        # タイムスタンプ降順（新しい順）で挿入、同一なら先頭
        for i, rp in enumerate(lst):
            _, ts = self.tsv_entries[rp]
            if timestamp >= ts:
                lst.insert(i, relpath)
                return
        # 末尾に追加
        lst.append(relpath)

    # Nodeファイルとnode_map.tsvの整合性チェック・自動修正
    def _check_and_update_node_map(self):
        # 1. node_map.tsvの読み込み＋キャッシュ初期化
        self.tsv_entries = {}
        self.uuid_map = {}
        if os.path.exists(self.map_path):
            with open(self.map_path, encoding="utf-8") as f:
                first = True
                for line in f:
                    if first:
                        # ヘッダ行ならスキップ
                        if line.strip().lower().startswith("relpath"):
                            first = False
                            continue
                        first = False
                    parts = line.strip().split("\t")
                    if len(parts) == 3:
                        self.add_node(*parts)

        # 2. nodes_dir配下の全XMLファイルを列挙しつつ不足分を即時追加
        changed = False
        for folder in os.listdir(self.nodes_dir):
            folder_path = os.path.join(self.nodes_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            for fname in os.listdir(folder_path):
                if fname.endswith(".xml") and len(fname) == 6:
                    relpath = f"{folder}/{fname}"
                    # 不足分を追加
                    if relpath not in self.tsv_entries:
                        xml_path = os.path.join(self.nodes_dir, folder, fname)
                        uuid, timestamp = _get_uuid_and_timestamp_from_xml(xml_path)
                        self.add_node(relpath, uuid, timestamp)
                        changed = True

        # 3. 過剰分（uuid_mapのどのリストにも含まれないrelpath）を削除
        all_uuid_relpaths = set()
        for relpaths in self.uuid_map.values():
            all_uuid_relpaths.update(relpaths)
        for relpath in list(self.tsv_entries.keys()):
            if relpath not in all_uuid_relpaths:
                self.tsv_entries.pop(relpath)
                changed = True

        # 4. フラグが立っていればTSV書き直し
        if changed:
            with open(self.map_path, "w", encoding="utf-8") as f:
                f.write("relpath\tuuid\ttimestamp\n")
                for relpath, (uuid, timestamp) in self.tsv_entries.items():
                    f.write(f"{relpath}\t{uuid}\t{timestamp}\n")

    def _get_next_relpath_and_folder(self):
        # TSVキャッシュベースで空きを探す
        used = set(self.tsv_entries.keys())
        for i in range(256):
            folder = f"{i:02x}"
            folder_path = os.path.join(self.nodes_dir, folder)
            os.makedirs(folder_path, exist_ok=True)
            for idx in range(256):
                filename = f"{idx:02x}.xml"
                relpath = f"{folder}/{filename}"
                if relpath not in used:
                    # 空きが見つかった場合、既存ファイルがあればUUIDとtimestampを取得してキャッシュ・TSVに追記
                    xml_path = os.path.join(folder_path, filename)
                    if os.path.exists(xml_path):
                        uuid, timestamp = _get_uuid_and_timestamp_from_xml(xml_path)
                        self.add_node(relpath, uuid, timestamp)
                        # TSV追記
                        with open(self.map_path, "a", encoding="utf-8") as f:
                            f.write(f"{relpath}\t{uuid}\t{timestamp}\n")
                    else:
                        return relpath
        raise Exception("ノード保存上限に達しました")

    def _generate_node_id(self):
        # UUIDベースのノードID
        node_id = str(uuid.uuid4())
        # 既存のUUIDと重複しないようにする
        while node_id in self.uuid_map:
            node_id = str(uuid.uuid4())
        return node_id

    def save_node(self, prompt, response, g):
        relpath = self._get_next_relpath_and_folder()
        node_path = os.path.join(self.base_dir, "nodes", relpath)

        # 新規作成
        node_id = self._generate_node_id()
        timestamp = datetime.now().astimezone()
        node = Node(
            id = node_id,
            timestamp = timestamp,
            contents = [
                {
                    "role": "user",
                    "count": g.prompt_count,
                    "duration": g.prompt_duration,
                    "text": prompt,
                },
                {
                    "role": "assistant",
                    "count": g.eval_count,
                    "duration": g.eval_duration,
                    "text": response,
                },
            ],
            model = g.model,
            summary = "",
            summary_updated = False,
            summary_last_built = timestamp,
            tags = [],
            path = node_path,
        )
        node.save()

        # キャッシュ・TSV追記
        self.add_node(relpath, node_id, timestamp)
        write_header = not os.path.exists(self.map_path)
        with open(self.map_path, "a", encoding="utf-8") as f:
            if write_header:
                f.write("relpath\tuuid\ttimestamp\n")
            f.write(f"{relpath}\t{node_id}\t{timestamp.isoformat()}\n")

        return node
