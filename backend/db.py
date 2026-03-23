from __future__ import annotations

import os
from dataclasses import dataclass
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
        self.password_resets = self.db["password_resets"]

        # Create basic indexes
        self.users.create_index("username", unique=True)
        self.users.create_index("email", unique=True, sparse=True)
        self.users.create_index("role")
        self.submissions.create_index("user_id")
        self.submissions.create_index("created_at")
        self.password_resets.create_index("token_hash", unique=True)
        self.password_resets.create_index("expires_at", expireAfterSeconds=0)
        self.password_resets.create_index("user_id")

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        role: str,
        created_at: Optional[datetime] = None,
    ) -> str:
        doc = {
            "username": username,
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "role": role,  # 'admin' | 'user'
            "created_at": created_at or self._now(),
        }
        res = self.users.insert_one(doc)
        return str(res.inserted_id)

    def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"username": username})

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"email": email.lower().strip()})

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    def save_password_reset_token(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> str:
        self.password_resets.delete_many({"user_id": user_id, "used_at": {"$exists": False}})
        doc = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "created_at": self._now(),
        }
        res = self.password_resets.insert_one(doc)
        return str(res.inserted_id)

    def find_valid_password_reset_by_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        now = self._now()
        return self.password_resets.find_one(
            {
                "token_hash": token_hash,
                "used_at": {"$exists": False},
                "expires_at": {"$gt": now},
            }
        )

    def mark_password_reset_used(self, reset_id: Any) -> None:
        self.password_resets.update_one(
            {"_id": reset_id},
            {"$set": {"used_at": self._now()}},
        )

    def update_user_password(self, user_id: str, password_hash: str) -> None:
        self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": password_hash, "password_updated_at": self._now()}},
        )

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

    @staticmethod
    def _serialize_dt(value: Any) -> Optional[str]:
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return None

    def get_admin_user_analytics(self, limit_users: int = 300) -> List[Dict[str, Any]]:
        """
        One row per registered user with submission aggregates (verdict mix, activity, modes).
        """
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        pipeline = [
            {
                "$group": {
                    "_id": "$user_id",
                    "total_submissions": {"$sum": 1},
                    "verdicts": {"$push": "$verdict"},
                    "modes": {"$push": "$fact_check_mode"},
                    "last_activity_at": {"$max": "$created_at"},
                    "first_activity_at": {"$min": "$created_at"},
                    "avg_confidence": {"$avg": "$confidence"},
                    "recent_7d": {
                        "$sum": {
                            "$cond": [{"$gte": ["$created_at", cutoff_7d]}, 1, 0]
                        }
                    },
                }
            }
        ]

        agg_by_uid: Dict[str, Dict[str, Any]] = {}
        for doc in self.submissions.aggregate(pipeline):
            uid = doc.get("_id")
            if uid is None:
                continue
            uid = str(uid)
            verdicts = [v for v in (doc.get("verdicts") or []) if v is not None]
            modes = [m for m in (doc.get("modes") or []) if m]
            vc = Counter(verdicts)
            mc = Counter(modes)
            total = int(doc["total_submissions"])
            fake = int(vc.get("FAKE NEWS", 0))
            real = int(vc.get("REAL NEWS", 0))
            unc = int(vc.get("UNCERTAIN", 0))

            avg_c = doc.get("avg_confidence")
            agg_by_uid[uid] = {
                "total_submissions": total,
                "verdict_breakdown": dict(vc),
                "fake_count": fake,
                "real_count": real,
                "uncertain_count": unc,
                "fake_share_pct": round(100.0 * fake / total, 1) if total else 0.0,
                "real_share_pct": round(100.0 * real / total, 1) if total else 0.0,
                "uncertain_share_pct": round(100.0 * unc / total, 1) if total else 0.0,
                "fact_check_mode_breakdown": dict(mc),
                "avg_confidence": round(float(avg_c), 2) if avg_c is not None else None,
                "first_activity_at": self._serialize_dt(doc.get("first_activity_at")),
                "last_activity_at": self._serialize_dt(doc.get("last_activity_at")),
                "submissions_last_7d": int(doc.get("recent_7d", 0)),
            }

        users = self.get_admin_users(limit=limit_users)
        out: List[Dict[str, Any]] = []
        empty = {
            "total_submissions": 0,
            "verdict_breakdown": {},
            "fake_count": 0,
            "real_count": 0,
            "uncertain_count": 0,
            "fake_share_pct": 0.0,
            "real_share_pct": 0.0,
            "uncertain_share_pct": 0.0,
            "fact_check_mode_breakdown": {},
            "avg_confidence": None,
            "first_activity_at": None,
            "last_activity_at": None,
            "submissions_last_7d": 0,
        }
        for u in users:
            uid = u["id"]
            analytics = dict(empty)
            analytics.update(agg_by_uid.get(uid, {}))
            row = dict(u)
            row["analytics"] = analytics
            out.append(row)

        out.sort(
            key=lambda r: (
                -(r.get("analytics") or {}).get("total_submissions", 0),
                (r.get("username") or "").lower(),
            )
        )
        return out

