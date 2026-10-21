from datetime import date, timedelta
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Compare active-reservation date-search timings with and without the "
        "availability index, using disposable synthetic data."
    )

    def add_arguments(self, parser):
        parser.add_argument("--rows", type=int, default=100_000)
        parser.add_argument("--runs", type=int, default=100)

    def handle(self, *args, **options):
        rows = options["rows"]
        runs = options["runs"]
        if rows < 1 or runs < 1:
            raise CommandError("--rows and --runs must both be positive integers")

        table = connection.ops.quote_name("hotel_room_index_benchmark")
        index = connection.ops.quote_name("room_index_benchmark_idx")
        sql = (
            f"SELECT room_id FROM {table} "
            "WHERE status IN (%s, %s) AND ("
            "(stay_type = %s AND check_in < %s AND check_out > %s) OR "
            "(stay_type = %s AND check_in >= %s AND check_in <= %s))"
        )
        check_in = date(2026, 5, 1)
        check_out = date(2026, 5, 8)
        params = (
            "Pending", "Checked-In", "Night", check_out, check_in,
            "Day", check_in, check_out,
        )

        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            cursor.execute(
                f"CREATE TEMPORARY TABLE {table} ("
                "id BIGINT PRIMARY KEY, room_id INTEGER NOT NULL, "
                "status VARCHAR(20) NOT NULL, stay_type VARCHAR(10) NOT NULL, "
                "check_in DATE NOT NULL, check_out DATE NOT NULL)"
            )
            try:
                base_date = date(2020, 1, 1)
                batch = []
                for row_id in range(rows):
                    arrival = base_date + timedelta(days=(row_id * 37) % 3650)
                    duration = 1 + row_id % 7
                    status = ("Pending", "Checked-In", "Checked-Out")[row_id % 10 // 4]
                    stay_type = "Night" if row_id % 4 else "Day"
                    batch.append((
                        row_id + 1,
                        row_id % 1000,
                        status,
                        stay_type,
                        arrival,
                        arrival + timedelta(days=duration),
                    ))
                    if len(batch) == 5000:
                        cursor.executemany(
                            f"INSERT INTO {table} "
                            "(id, room_id, status, stay_type, check_in, check_out) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            batch,
                        )
                        batch.clear()
                if batch:
                    cursor.executemany(
                        f"INSERT INTO {table} "
                        "(id, room_id, status, stay_type, check_in, check_out) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        batch,
                    )

                cursor.execute(f"ANALYZE {table}")
                no_index_plan = self._explain(cursor, sql, params)
                no_index_ms = self._time_query(cursor, sql, params, runs)

                cursor.execute(
                    f"CREATE INDEX {index} ON {table} "
                    "(status, check_in, check_out, room_id)"
                )
                cursor.execute(f"ANALYZE {table}")
                indexed_plan = self._explain(cursor, sql, params)
                indexed_ms = self._time_query(cursor, sql, params, runs)
            finally:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

        speedup = no_index_ms / indexed_ms if indexed_ms else float("inf")
        self.stdout.write(f"Database: {connection.vendor}")
        self.stdout.write(f"Synthetic rows (temporary table only): {rows:,}")
        self.stdout.write(f"Search runs per measurement: {runs:,}")
        self.stdout.write(f"Without index: {no_index_ms:.3f} ms/query")
        self.stdout.write(f"With index:    {indexed_ms:.3f} ms/query")
        self.stdout.write(f"Speed-up:      {speedup:.2f}x")
        self.stdout.write(f"Plan without index: {no_index_plan}")
        self.stdout.write(f"Plan with index:    {indexed_plan}")
        self.stdout.write(
            "Note: timings use a representative synthetic availability search; "
            "real gains depend on database, row count, and date selectivity."
        )

    @staticmethod
    def _time_query(cursor, sql, params, runs):
        # Warm up the statement/cache before timing repeated executions.
        for _ in range(min(5, runs)):
            cursor.execute(sql, params)
            cursor.fetchall()

        started = perf_counter()
        for _ in range(runs):
            cursor.execute(sql, params)
            cursor.fetchall()
        return (perf_counter() - started) * 1000 / runs

    @staticmethod
    def _explain(cursor, sql, params):
        if connection.vendor == "sqlite":
            explain = "EXPLAIN QUERY PLAN "
        elif connection.vendor == "postgresql":
            explain = "EXPLAIN (COSTS OFF) "
        else:
            explain = "EXPLAIN "
        cursor.execute(explain + sql, params)
        return "; ".join(str(row[-1]) for row in cursor.fetchall())
