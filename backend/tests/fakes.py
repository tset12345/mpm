class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.mode = "select"
        self.payload = None
        self.on_conflict = None
        self.filters = []
        self.orders = []
        self.limit_n = None
        self.range_ = None

    def select(self, *_a, **_k):
        self.mode = "select"
        return self

    def insert(self, row):
        self.mode, self.payload = "insert", row
        return self

    def upsert(self, row, on_conflict=None):
        self.mode, self.payload, self.on_conflict = "upsert", row, on_conflict
        return self

    def update(self, values):
        self.mode, self.payload = "update", values
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and r.get(col) >= val)
        return self

    def order(self, col, desc=False):
        self.orders.append((col, desc))
        return self

    def range(self, lo, hi):
        self.range_ = (lo, hi)
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def _matching(self):
        return [r for r in self.db.tables.setdefault(self.name, []) if all(f(r) for f in self.filters)]

    def execute(self):
        table = self.db.tables.setdefault(self.name, [])
        if self.mode == "insert":
            row = dict(self.payload)
            row.setdefault("id", self.db.next_id())
            table.append(row)
            return _Result([row])
        if self.mode == "upsert":
            keys = (self.on_conflict or "id").split(",")
            for r in table:
                if all(r.get(k) == self.payload.get(k) for k in keys):
                    r.update(self.payload)
                    return _Result([r])
            row = dict(self.payload)
            row.setdefault("id", self.db.next_id())
            table.append(row)
            return _Result([row])
        if self.mode == "update":
            rows = self._matching()
            for r in rows:
                r.update(self.payload)
            return _Result(rows)
        if self.mode == "delete":
            rows = self._matching()
            self.db.tables[self.name] = [r for r in table if r not in rows]
            return _Result(rows)
        rows = self._matching()
        for col, desc in reversed(self.orders):
            rows = sorted(rows, key=lambda r, c=col: (r.get(c) is None, r.get(c) if r.get(c) is not None else 0),
                          reverse=desc)
        if self.range_ is not None:
            lo, hi = self.range_
            rows = rows[lo: hi + 1]
        if self.limit_n is not None:
            rows = rows[: self.limit_n]
        rows = rows[: self.db.max_rows]
        return _Result([dict(r) for r in rows])


class FakeSupabase:
    """supabase-py의 table().select/insert/upsert/update/delete 체인을 흉내 내는 메모리 DB."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self._id = 0
        self.max_rows = 1000  # PostgREST 기본 응답 상한

    def next_id(self):
        self._id += 1
        return self._id

    def table(self, name):
        return _Query(self, name)

    def seed(self, name, rows):
        added = []
        for r in rows:
            row = dict(r)
            row.setdefault("id", self.next_id())
            self.tables.setdefault(name, []).append(row)
            added.append(row)
        return added
