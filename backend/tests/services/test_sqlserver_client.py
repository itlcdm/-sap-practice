from unittest.mock import MagicMock

from app.services import sqlserver_client


async def test_fetch_stored_procedure_rows_returns_columns_and_rows(monkeypatch):
    fake_cursor = MagicMock()
    fake_cursor.description = [("ItemCode",), ("Stock",)]
    fake_cursor.fetchall.return_value = [("A00001", 10), ("A00002", 5)]

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.__exit__.return_value = False
    fake_conn.cursor.return_value = fake_cursor

    connect_calls = []

    def fake_connect(connection_string):
        connect_calls.append(connection_string)
        return fake_conn

    monkeypatch.setattr(sqlserver_client.pyodbc, "connect", fake_connect)

    columns, rows = await sqlserver_client.fetch_stored_procedure_rows("DRIVER=x;", "ALCONSIT")

    assert columns == ["ItemCode", "Stock"]
    assert rows == [("A00001", 10), ("A00002", 5)]
    assert connect_calls == ["DRIVER=x;"]
    fake_cursor.execute.assert_called_once_with("{CALL ALCONSIT}")
