# 稿迹 ManuTrace 发布清单（2026-07-05）

## 当前结论

- 包名/CLI：`manutrace`
- 当前版本：`0.1.0a1`
- License：MIT
- 发布形态：GitHub 开源仓库优先，Python CLI + Codex skill 文件夹
- 当前状态：sanitized 开源仓库已推送 GitHub 公开远程
- 公开仓库：`https://github.com/wmglimpser-hash/manutrace`
- 本地 tag：`v0.1.0a1`

## 已核验

- npm：`npm view manutrace name version description` 返回 E404，未发现同名包。
- PyPI：`python -m pip index versions manutrace` 返回 `No matching distribution found for manutrace`。
- GitHub：公开搜索未见明显同名 `manutrace` 仓库；GitHub 仓库名非全局唯一，发布前仍建议用目标 owner 精确确认。
- Privacy：current working tree and reachable git history were scanned before publication.

## 发布前必须由作者确认

- GitHub 公开仓库 owner 与认证方式。
- PyPI 发布账号与 owner；当前暂不上传 PyPI。
- 是否同时发布 npm 占名包；当前实现是 Python CLI，不建议在无 Node wrapper 时发布 npm 功能包。
- 是否把 `skills/manutrace/` 安装到全局 Codex skill 目录或单独发布为 skill 仓库。

## 发布命令草案

```powershell
$env:PYTHONUTF8="1"
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

真实上传前必须重新运行本清单并得到作者确认。
