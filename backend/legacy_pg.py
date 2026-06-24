import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import delete, select

from db_models import LegacyDocument


def _now():
    return datetime.now(timezone.utc)


def _clean_projection(doc: Dict[str, Any], projection: Optional[Dict[str, int]]):
    if not projection:
        return copy.deepcopy(doc)
    result = copy.deepcopy(doc)
    for key, include in projection.items():
        if key == "_id" and include == 0:
            result.pop("_id", None)
        elif include == 0:
            result.pop(key, None)
    return result


def _get_value(doc: Dict[str, Any], key: str):
    value = doc
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _matches_operator(value: Any, op: str, expected: Any) -> bool:
    if op == "$gte":
        return value is not None and value >= expected
    if op == "$gt":
        return value is not None and value > expected
    if op == "$lte":
        return value is not None and value <= expected
    if op == "$lt":
        return value is not None and value < expected
    if op == "$ne":
        return value != expected
    if op == "$in":
        return value in expected
    if op == "$regex":
        import re

        flags = re.IGNORECASE
        return value is not None and re.search(expected, str(value), flags) is not None
    return value == expected


def _matches(doc: Dict[str, Any], query: Optional[Dict[str, Any]]) -> bool:
    if not query:
        return True
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, sub_query) for sub_query in expected):
                return False
            continue
        value = _get_value(doc, key)
        if isinstance(expected, dict):
            for op, op_value in expected.items():
                if op == "$options":
                    continue
                if not _matches_operator(value, op, op_value):
                    return False
        elif value != expected:
            return False
    return True


def _sort_docs(docs: List[Dict[str, Any]], sort_spec: Optional[Any]):
    if not sort_spec:
        return docs
    if isinstance(sort_spec, str):
        sort_fields = [(sort_spec, 1)]
    elif isinstance(sort_spec, tuple):
        sort_fields = [sort_spec]
    else:
        sort_fields = list(sort_spec)

    for field, direction in reversed(sort_fields):
        docs.sort(key=lambda doc: (_get_value(doc, field) is None, _get_value(doc, field)), reverse=direction == -1)
    return docs


def _apply_set(doc: Dict[str, Any], updates: Dict[str, Any]):
    for key, value in updates.items():
        target = doc
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value


class DocumentCursor:
    def __init__(self, docs: List[Dict[str, Any]], projection: Optional[Dict[str, int]] = None):
        self.docs = docs
        self.projection = projection

    def sort(self, *args):
        sort_spec = args[0] if len(args) == 1 else args
        _sort_docs(self.docs, sort_spec)
        return self

    async def to_list(self, length: int):
        docs = self.docs[:length] if length else self.docs
        return [_clean_projection(doc, self.projection) for doc in docs]


class DocumentAggregateCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs

    async def to_list(self, length: int):
        return self.docs[:length] if length else self.docs


class PostgresDocumentCollection:
    def __init__(self, session_factory, name: str):
        self.session_factory = session_factory
        self.name = name

    async def _all_docs(self):
        async with self.session_factory() as session:
            result = await session.execute(select(LegacyDocument).where(LegacyDocument.collection == self.name))
            return [copy.deepcopy(row.data) for row in result.scalars().all()]

    async def _matching_rows(self, session, query):
        result = await session.execute(select(LegacyDocument).where(LegacyDocument.collection == self.name))
        rows = result.scalars().all()
        return [row for row in rows if _matches(row.data, query)]

    async def find_one(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, int]] = None, sort: Optional[Any] = None):
        docs = [doc for doc in await self._all_docs() if _matches(doc, query)]
        _sort_docs(docs, sort)
        return _clean_projection(docs[0], projection) if docs else None

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, int]] = None):
        async def load():
            return [doc for doc in await self._all_docs() if _matches(doc, query)]

        class AwaitableCursor:
            def __init__(self):
                self._sort = None

            def sort(self, *args):
                self._sort = args[0] if len(args) == 1 else args
                return self

            async def to_list(self, length: int):
                docs = await load()
                _sort_docs(docs, self._sort)
                docs = docs[:length] if length else docs
                return [_clean_projection(doc, projection) for doc in docs]

        return AwaitableCursor()

    async def insert_one(self, doc: Dict[str, Any]):
        data = copy.deepcopy(doc)
        data.setdefault("id", str(uuid.uuid4()))
        doc_id = str(data.get("id") or data.get("_id") or uuid.uuid4())
        async with self.session_factory() as session:
            session.add(LegacyDocument(collection=self.name, doc_id=doc_id, data=data, created_at=_now()))
            await session.commit()
        return type("InsertOneResult", (), {"inserted_id": doc_id})()

    async def insert_many(self, docs: Iterable[Dict[str, Any]]):
        inserted = []
        async with self.session_factory() as session:
            for doc in docs:
                data = copy.deepcopy(doc)
                data.setdefault("id", str(uuid.uuid4()))
                doc_id = str(data.get("id") or data.get("_id") or uuid.uuid4())
                inserted.append(doc_id)
                session.add(LegacyDocument(collection=self.name, doc_id=doc_id, data=data, created_at=_now()))
            await session.commit()
        return type("InsertManyResult", (), {"inserted_ids": inserted})()

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        async with self.session_factory() as session:
            rows = await self._matching_rows(session, query)
            matched = 1 if rows else 0
            if rows:
                doc = copy.deepcopy(rows[0].data)
                if "$set" in update:
                    _apply_set(doc, update["$set"])
                rows[0].data = doc
                rows[0].modified_at = _now()
            await session.commit()
        return type("UpdateResult", (), {"matched_count": matched, "modified_count": matched})()

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        async with self.session_factory() as session:
            rows = await self._matching_rows(session, query)
            for row in rows:
                doc = copy.deepcopy(row.data)
                if "$set" in update:
                    _apply_set(doc, update["$set"])
                row.data = doc
                row.modified_at = _now()
            await session.commit()
        return type("UpdateResult", (), {"matched_count": len(rows), "modified_count": len(rows)})()

    async def delete_many(self, query: Dict[str, Any]):
        async with self.session_factory() as session:
            rows = await self._matching_rows(session, query)
            for row in rows:
                await session.delete(row)
            await session.commit()
        return type("DeleteResult", (), {"deleted_count": len(rows)})()

    async def delete_one(self, query: Dict[str, Any]):
        async with self.session_factory() as session:
            rows = await self._matching_rows(session, query)
            if rows:
                await session.delete(rows[0])
            await session.commit()
        return type("DeleteResult", (), {"deleted_count": 1 if rows else 0})()

    async def drop(self):
        async with self.session_factory() as session:
            await session.execute(delete(LegacyDocument).where(LegacyDocument.collection == self.name))
            await session.commit()

    async def count_documents(self, query: Optional[Dict[str, Any]] = None):
        return len([doc for doc in await self._all_docs() if _matches(doc, query)])

    async def create_index(self, *args, **kwargs):
        return "postgres_json_index"

    def aggregate(self, pipeline: List[Dict[str, Any]]):
        async def run():
            docs = await self._all_docs()
            for stage in pipeline:
                if "$match" in stage:
                    docs = [doc for doc in docs if _matches(doc, stage["$match"])]
                elif "$group" in stage:
                    docs = self._group(docs, stage["$group"])
            return docs

        class AwaitableAggregate:
            async def to_list(self, length: int):
                docs = await run()
                return docs[:length] if length else docs

        return AwaitableAggregate()

    def _eval_expr(self, doc: Dict[str, Any], expr: Any):
        if isinstance(expr, str) and expr.startswith("$"):
            return _get_value(doc, expr[1:]) or 0
        if isinstance(expr, dict) and "$multiply" in expr:
            total = 1
            for item in expr["$multiply"]:
                total *= self._eval_expr(doc, item)
            return total
        if isinstance(expr, dict) and "$abs" in expr:
            return abs(self._eval_expr(doc, expr["$abs"]))
        if isinstance(expr, dict) and "$cond" in expr:
            condition, truthy, falsy = expr["$cond"]
            return self._eval_condition(doc, condition) and self._eval_expr(doc, truthy) or self._eval_expr(doc, falsy)
        return expr

    def _eval_condition(self, doc: Dict[str, Any], condition: Any):
        if isinstance(condition, dict):
            if "$gt" in condition:
                left, right = condition["$gt"]
                return self._eval_expr(doc, left) > self._eval_expr(doc, right)
            if "$lt" in condition:
                left, right = condition["$lt"]
                return self._eval_expr(doc, left) < self._eval_expr(doc, right)
        return bool(condition)

    def _group_key(self, doc: Dict[str, Any], spec: Any):
        if isinstance(spec, str):
            return self._eval_expr(doc, spec)
        if isinstance(spec, dict):
            return {key: self._eval_expr(doc, value) for key, value in spec.items()}
        return spec

    def _group(self, docs: List[Dict[str, Any]], spec: Dict[str, Any]):
        grouped: Dict[str, Dict[str, Any]] = {}
        for doc in docs:
            key = self._group_key(doc, spec["_id"])
            key_hash = repr(key)
            row = grouped.setdefault(key_hash, {"_id": key})
            for out_key, agg in spec.items():
                if out_key == "_id":
                    continue
                if "$sum" in agg:
                    row[out_key] = row.get(out_key, 0) + self._eval_expr(doc, agg["$sum"])
        return list(grouped.values())


class PostgresDocumentStore:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __getattr__(self, name: str):
        return PostgresDocumentCollection(self.session_factory, name)

    def __getitem__(self, name: str):
        return PostgresDocumentCollection(self.session_factory, name)

    async def list_collection_names(self):
        async with self.session_factory() as session:
            result = await session.execute(select(LegacyDocument.collection).distinct())
            return list(result.scalars().all())

    async def command(self, name: str):
        if name == "dbStats":
            async with self.session_factory() as session:
                result = await session.execute(select(LegacyDocument))
                docs = result.scalars().all()
                size = sum(len(str(doc.data)) for doc in docs)
                return {"dataSize": size, "indexSize": 0, "storageSize": size}
        return {}
