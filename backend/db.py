from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
# Also support a backend-local .env for app-specific settings
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


@dataclass(frozen=True)
class DbConfig:
    uri: str
    db_name: str


def _get_db_config() -> DbConfig:
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise RuntimeError("Missing MONGODB_URI in environment/.env")
    return DbConfig(uri=uri, db_name=os.getenv("MONGODB_DB", "newsveritas"))


class AppDB:
    def __init__(self) -> None:
        cfg = _get_db_config()
        self.client = MongoClient(cfg.uri)
        self.db = self.client[cfg.db_name]

        self.users = self.db["users"]
        self.submissions = self.db["submissions"]

        # Create basic indexes
        self.users.create_index("username", unique=True)
        self.users.create_index("role")
        self.submissions.create_index("user_id")
        self.submissions.create_index("created_at")

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        created_at: Optional[datetime] = None,
    ) -> str:
        doc = {
            "username": username,
            "password_hash": password_hash,
            "role": role,  # 'admin' | 'user'
            "created_at": created_at or self._now(),
        }
        res = self.users.insert_one(doc)
        return str(res.inserted_id)

    def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"username": username})

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"_id": ObjectId(user_id)})

    def add_submission(self, *, user_id: str, payload: Dict[str, Any]) -> str:
        payload = dict(payload)
        payload["user_id"] = user_id
        payload["created_at"] = payload.get("created_at") or self._now()
        res = self.submissions.insert_one(payload)
        return str(res.inserted_id)

    def get_submissions_for_user(self, user_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        cur = (
            self.submissions.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [self._serialize_submission(doc) for doc in cur]

    def get_admin_overview(self, limit: int = 50) -> Dict[str, Any]:
        total = self.submissions.count_documents({})
        fake = self.submissions.count_documents({"verdict": "FAKE NEWS"})
        real = self.submissions.count_documents({"verdict": "REAL NEWS"})
        recent = list(
            self.submissions.find({}).sort("created_at", -1).limit(limit)
        )
        return {
            "totalSubmissions": total,
            "fakeCount": fake,
            "realCount": real,
            "recentSubmissions": [self._serialize_submission(d) for d in recent],
        }

    def get_recent_submissions_admin(self, limit: int = 50) -> list[Dict[str, Any]]:
        cur = self.submissions.find({}).sort("created_at", -1).limit(limit)
        return [self._serialize_submission(d) for d in cur]

    def get_admin_users(self, limit: int = 100) -> list[Dict[str, Any]]:
        cur = self.users.find({}).sort("created_at", -1).limit(limit)
        out = []
        for u in cur:
            u = dict(u)
            u["id"] = str(u.pop("_id"))
            # Hide password hash
            u.pop("password_hash", None)
            if isinstance(u.get("created_at"), datetime):
                u["created_at"] = u["created_at"].isoformat() + "Z"
            out.append(u)
        return out

    @staticmethod
    def _serialize_submission(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat() + "Z"
        return doc

