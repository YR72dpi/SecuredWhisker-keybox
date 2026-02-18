from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

import fcntl


JsonDict = Dict[str, Any]
PathLike = Union[str, os.PathLike]


def _data_json_path(path: Optional[PathLike] = None) -> Path:
	"""Chemin vers data.json (par défaut: fichier data.json à côté de ce module)."""
	if path is None:
		return Path(__file__).resolve().parent / "data.json"
	return Path(path)


def get_all_json(path: Optional[PathLike] = None) -> JsonDict:
	"""Récupère tout le contenu de data.json."""
	json_path = _data_json_path(path)
	if not json_path.exists():
		return {}

	with json_path.open("r", encoding="utf-8") as f:
		fcntl.flock(f.fileno(), fcntl.LOCK_SH)
		try:
			raw = f.read().strip()
			if not raw:
				return {}
			data = json.loads(raw)
			if not isinstance(data, dict):
				raise ValueError("Le JSON racine doit être un objet (dict).")
			return data
		finally:
			fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def update_value(
	key_path: str,
	value: Any,
	*,
	path: Optional[PathLike] = None,
	create_missing: bool = True,
) -> None:
	"""Met à jour une valeur dans data.json.

	- key_path: chemin "a.b.c" (ex: "initialized" ou "keypair.public")
	- value: valeur JSON (str/bool/dict/list/None/...)
	- create_missing: crée les objets intermédiaires si absents
	"""
	if not isinstance(key_path, str) or not key_path.strip():
		raise ValueError("key_path invalide")

	json_path = _data_json_path(path)
	json_path.parent.mkdir(parents=True, exist_ok=True)

	# Lock exclusif via fichier .lock (évite les interférences)
	lock_path = json_path.with_suffix(json_path.suffix + ".lock")
	with lock_path.open("w", encoding="utf-8") as lockf:
		fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
		try:
			data = get_all_json(json_path)
			_set_by_path(data, key_path, value, create_missing=create_missing)
			_atomic_write_json(json_path, data)
		finally:
			fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def _set_by_path(root: JsonDict, key_path: str, value: Any, *, create_missing: bool) -> None:
	parts = [p for p in key_path.split(".") if p]
	if not parts:
		raise ValueError("key_path vide")

	cur: Any = root
	for part in parts[:-1]:
		if not isinstance(cur, dict):
			raise ValueError(f"Parent non-objet sur '{part}'")
		if part not in cur:
			if not create_missing:
				raise KeyError(part)
			cur[part] = {}
		elif not isinstance(cur[part], dict):
			if not create_missing:
				raise ValueError(f"Segment '{part}' n'est pas un objet")
			cur[part] = {}
		cur = cur[part]

	if not isinstance(cur, dict):
		raise ValueError("Parent non-objet")
	cur[parts[-1]] = value


def _atomic_write_json(path: Path, data: JsonDict) -> None:
	payload = json.dumps(data, ensure_ascii=False, indent=4) + "\n"
	fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
	try:
		with os.fdopen(fd, "w", encoding="utf-8") as f:
			f.write(payload)
			f.flush()
			os.fsync(f.fileno())
		os.replace(tmp_name, str(path))
	finally:
		# si os.replace a échoué, nettoyage best-effort
		try:
			if os.path.exists(tmp_name):
				os.remove(tmp_name)
		except OSError:
			pass

