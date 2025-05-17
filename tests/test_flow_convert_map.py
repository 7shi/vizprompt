import re
from vizprompt.core.flow import Flow

def make_flow_map(flowchart):
    nodes, conn = set(), []
    for line in flowchart.strip().splitlines():
        # 1 --> 2
        if m := re.match(r" *(\d+) *--> *(\d+)", line):
            f, t = m.groups()
            nodes.add(int(f))
            nodes.add(int(t))
            conn.append((f, t))
    flow = Flow(
        id="dummy",
        name="test",
        created=None,
        updated=None,
        description="",
        nodes=[str(n) for n in sorted(nodes)],
        connections=conn,
        data_dir=".",
        relpath="dummy.yaml",
    )
    hs = flow.get_histories()
    return ["\n".join(flow.convert_map(h)) for h in hs]

def test_convert_map_1():
    result = make_flow_map("""
    1 --> 2
    2 --> 3
    3 --> 4
""")
    expected = ["1→2→3→4"]
    assert result == expected

def test_convert_map_2():
    result = make_flow_map("""
    1 --> 2
    2 --> 3
    2 --> 4
""")
    expected = ["""
1→2<
  2<3
  2<4
""".strip()]
    assert result == expected

def test_convert_map_3():
    result = make_flow_map("""
    1 --> 3
    2 --> 3
    3 --> 4
""")
    expected = ["""
1>3
  2>3
  >3→4
""".strip()]
    assert result == expected

def test_convert_map_4():
    result = make_flow_map("""
    1 --> 2
    2 --> 3
    2 --> 4
    3 --> 5
    4 --> 5
    5 --> 6
""")
    expected = ["""
1→2<
  2<3>5
  2<4>5
  >5→6
""".strip()]
    assert result == expected

def test_convert_map_5():
    result = make_flow_map("""
    1 --> 2
    2 --> 3
    2 --> 5
    3 --> 4
    5 --> 6
    4 --> 7
    6 --> 7
    7 --> 8
""")
    expected = ["""
1→2<
  2<3→4>7
  2<5→6>7
  >7→8
""".strip()]
    assert result == expected

def test_convert_map_6():
    result = make_flow_map("""
    1 --> 2
    2 --> 3
    2 --> 4
    2 --> 5
    3 --> 6
    4 --> 6
    5 --> 6
    6 --> 7
""")
    expected = ["""
1→2<
  2<3>6
  2<4>6
  2<5>6
  >6→7
""".strip()]
    assert result == expected
