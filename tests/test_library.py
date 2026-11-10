from radial import library as lib


def test_scan_and_search(tmp_path):
    (tmp_path / "Clay").mkdir()
    (tmp_path / "Clay" / "ClayBuildup.ZBP").write_bytes(b"x")
    (tmp_path / "Clay" / "notes.txt").write_text("x")
    (tmp_path / "Hard").mkdir()
    (tmp_path / "Hard" / "TrimDynamic.zbp").write_bytes(b"x")

    found = lib.scan([tmp_path, tmp_path])  # pasta repetida não duplica
    assert [b["name"] for b in found] == ["ClayBuildup", "TrimDynamic"]
    assert [b["name"] for b in lib.search(found, "trim")] == ["TrimDynamic"]
    assert [b["name"] for b in lib.search(found, "clay build")] == ["ClayBuildup"]

    slot = lib.as_slot(found[0])
    assert slot["action"]["type"] == "brush_file"


def test_missing_folder_is_ignored(tmp_path):
    assert lib.scan([tmp_path / "nao-existe"]) == []
