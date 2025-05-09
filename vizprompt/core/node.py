import os, uuid
from datetime import datetime

import xml.etree.ElementTree as ET
from xml.dom.minidom import Document

def _get_uuid_and_timestamp_from_xml(path):
    """
    XMLファイルのルート要素id属性とtimestamp属性を取得（なければゼロUUIDと空文字を返す）
    """
    try:
        for _, elem in ET.iterparse(path, events=("start",)):
            if elem.tag == "node":
                uuid_str = elem.attrib.get("id", str(uuid.UUID(int=0)))
                timestamp = elem.attrib.get("timestamp", "")
                return uuid_str, timestamp
            else:
                break
    except Exception:
        pass
    return str(uuid.UUID(int=0)), ""

class Node:
    """
    XMLノード情報と一対一対応するデータクラス
    """
    def __init__(
        self,
        *, # 引数名を指定して渡す
        id: str,
        timestamp: datetime,
        prompt: str,
        response: str,
        model: str,
        user_count: int,
        user_duration: float,
        assistant_count: int,
        assistant_duration: float,
        summary: str,
        summary_updated: bool,
        summary_last_built: datetime,
        tags: list,
        path: str,
    ):
        self.id = id
        self.timestamp = timestamp
        self.prompt = prompt
        self.response = response
        self.model = model
        self.user_count = user_count
        self.user_duration = user_duration
        self.assistant_count = assistant_count
        self.assistant_duration = assistant_duration
        self.summary = summary
        self.summary_updated = summary_updated
        self.summary_last_built = summary_last_built
        self.tags = tags
        self.path = path

    def to_xml(self) -> str:
        """
        NodeインスタンスをXML文字列に変換
        """
        doc = Document()
        node = doc.createElement('node')
        node.setAttribute('id', self.id)
        node.setAttribute('timestamp', self.timestamp.astimezone().isoformat())
        doc.appendChild(node)
        prompt = doc.createElement('prompt')
        prompt.appendChild(doc.createCDATASection(f'\n{self.prompt.rstrip()}\n'))
        node.appendChild(prompt)
        response = doc.createElement('response')
        response.appendChild(doc.createCDATASection(f'\n{self.response.rstrip()}\n'))
        node.appendChild(response)
        metadata = doc.createElement('metadata')
        model = doc.createElement('model')
        model.appendChild(doc.createTextNode(self.model))
        metadata.appendChild(model)
        stats_user = doc.createElement('stats')
        stats_user.setAttribute('role', 'user')
        stats_user.setAttribute('count', str(self.user_count))
        stats_user.setAttribute('duration', f'{self.user_duration:.2f}')
        user_rate = self.user_count / self.user_duration if self.user_duration > 0 else 0
        stats_user.setAttribute('rate', f'{user_rate:.2f}')
        metadata.appendChild(stats_user)
        stats_assistant = doc.createElement('stats')
        stats_assistant.setAttribute('role', 'assistant')
        stats_assistant.setAttribute('count', str(self.assistant_count))
        stats_assistant.setAttribute('duration', f'{self.assistant_duration:.2f}')
        assistant_rate = self.assistant_count / self.assistant_duration if self.assistant_duration > 0 else 0
        stats_assistant.setAttribute('rate', f'{assistant_rate:.2f}')
        metadata.appendChild(stats_assistant)
        summary = doc.createElement('summary')
        summary.setAttribute('updated', str(self.summary_updated).lower())
        summary.setAttribute('last_built', self.summary_last_built.astimezone().isoformat())
        summary.appendChild(doc.createTextNode(self.summary))
        metadata.appendChild(summary)
        tags = doc.createElement('tags')
        for tag in self.tags:
            tag_elem = doc.createElement('tag')
            tag_elem.appendChild(doc.createTextNode(tag))
            tags.appendChild(tag_elem)
        metadata.appendChild(tags)
        node.appendChild(metadata)
        return doc.toprettyxml(encoding='utf-8', indent='').decode('utf-8')

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
        self.uuid_map.setdefault(uuid, []).append(relpath)

    # Nodeファイルとnode_map.tsvの整合性チェック・自動修正
    def _check_and_update_node_map(self):
        # 1. node_map.tsvの読み込み＋キャッシュ初期化
        self.tsv_entries = {}
        self.uuid_map = {}
        if os.path.exists(self.map_path):
            with open(self.map_path, encoding="utf-8") as f:
                for line in f:
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

        # 3. 過剰分を削除
        for relpath in list(self.tsv_entries.keys()):
            if relpath not in self.uuid_map:
                self.tsv_entries.pop(relpath)
                changed = True

        # 4. フラグが立っていればTSV書き直し
        if changed:
            with open(self.map_path, "w", encoding="utf-8") as f:
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
        timestamp = datetime.now()
        node = Node(
            id = node_id,
            timestamp = timestamp,
            prompt = prompt,
            response = response,
            model = g.model,
            user_count = getattr(g, "prompt_count", 0),
            user_duration = getattr(g, "prompt_duration", 0.0),
            assistant_count = getattr(g, "eval_count", 0),
            assistant_duration = getattr(g, "eval_duration", 0.0),
            summary = "",
            summary_updated = False,
            summary_last_built = timestamp,
            tags = [],
            path = node_path,
        )
        node.save()

        # キャッシュ・TSV追記
        self.add_node(relpath, node_id, timestamp)
        with open(self.map_path, "a", encoding="utf-8") as f:
            f.write(f"{relpath}\t{node_id}\t{timestamp}\n")

        return node
