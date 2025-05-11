import os, uuid
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom.minidom import Document
from vizprompt.core.base import BaseManager

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

    @classmethod
    def load(cls, path):
        """
        XMLファイルからNodeインスタンスを読み込む
        """
        tree = ET.parse(path)
        root = tree.getroot()
        node_id = root.attrib["id"]
        timestamp = datetime.fromisoformat(root.attrib["timestamp"])
        contents = []
        for content in root.findall(".//content"):
            role = content.attrib["role"]
            count = int(content.attrib["count"])
            duration = float(content.attrib["duration"])
            text = content.text or ""
            contents.append({
                "role": role,
                "count": count,
                "duration": duration,
                "text": text,
            })
        model = root.findtext(".//model")
        summary_node = root.find(".//summary")
        summary = summary_node.text or ""
        summary_updated = summary_node.attrib["updated"] == "true"
        summary_last_built = datetime.fromisoformat(summary_node.attrib["last_built"])
        tags = [tag.text for tag in root.findall(".//tag")]

        return cls(
            id=node_id,
            timestamp=timestamp,
            contents=contents,
            model=model,
            summary=summary,
            summary_updated=summary_updated,
            summary_last_built=summary_last_built,
            tags=tags,
            path=path,
        )

class NodeManager(BaseManager):
    def __init__(self, base_dir="project"):
        self.base_dir = base_dir
        self.cache = {}
        super().__init__(
            data_dir=os.path.join(base_dir, "nodes"),
            ext="xml",
        )

    def get_uuid_and_timestamp_from_file(self, path):
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

    def get_node(self, node_id):
        """
        UUIDからNodeインスタンスを取得
        """
        if node := self.cache.get(node_id):
            # キャッシュにある場合はキャッシュから取得
            return node
        if node_id in self.uuid_map:
            # キャッシュにない場合はファイルから読み込む
            relpath = self.uuid_map[node_id][0]
            path = os.path.join(self.data_dir, relpath)
            node = Node.load(path)
            self.cache[node_id] = node
            return node
        raise FileNotFoundError(f"Node with ID {node_id} not found.")

    def create_node(self, prompt, response, g):
        relpath = self.get_next_relpath_and_folder()
        node_path = os.path.join(self.data_dir, relpath)

        # 新規作成
        node_id = self.generate_uuid()
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
        self.cache[node_id] = node
        self.add_entry(relpath, node_id, timestamp)
        self.append_index(relpath, node_id, timestamp)

        return node
