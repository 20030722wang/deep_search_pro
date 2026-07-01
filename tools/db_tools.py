"""MySQL 数据库查询工具集 — 3 个 LangChain Tool"""
import re
from typing import List

from mysql.connector import connect, Error
from langchain_core.tools import tool

from app.core import settings, get_logger
from api.monitor import monitor

logger = get_logger(__name__)

# 表名安全校验：只允许字母、数字、下划线、中文
_VALID_TABLE_NAME_RE = re.compile(r'^[a-zA-Z0-9_一-鿿]+$')


def _validate_table_name(table_name: str) -> bool:
    """校验表名是否合法，防止 SQL 注入"""
    return bool(_VALID_TABLE_NAME_RE.match(table_name))


def _get_connection():
    """获取 MySQL 连接（配置从集中 settings 读取）"""
    return connect(**settings.mysql.to_conn_dict())


@tool
def list_sql_tables() -> str:
    """
    查询当前库中所有可用的表。
    供模型识别有哪些可用表，便于后续自定义 SQL 查询。

    Returns:
        有表: "可用的表有：表1, 表2, 表3..."
        无表: "没有可用的表"
        异常: "查询出现异常：异常信息"
    """
    monitor.report_tool(tool_name="数据库表名查询工具：list_sql_tables", args={})

    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                if not tables:
                    return "没有可用的表"
                table_names: List[str] = [table[0] for table in tables]
                return f"可用的表有：{', '.join(table_names)}"
    except Error as e:
        logger.exception("Failed to list SQL tables")
        return f"查询出现异常：{str(e)}"


@tool
def get_table_data(table_name: str) -> str:
    """
    查询指定表名的数据。调用之前必须先调用 list_sql_tables 完成表名校验。
    可用于单表数据查询和多表查询前的结构预览。

    Args:
        table_name: 表名

    Returns:
        CSV 格式数据：第一行列头，第二行起为数据，至多 100 条
    """
    monitor.report_tool(
        tool_name="数据库表数据查询工具：get_table_data",
        args={"table_name": table_name},
    )

    if not _validate_table_name(table_name):
        return f"错误：无效的表名 '{table_name}'，表名只能包含字母、数字、下划线和中文"

    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 100")
                description = cursor.description
                if not description:
                    return f"数据表：{table_name} 为空没有数据！"
                columns = [desc[0] for desc in description]
                rows = cursor.fetchall()
                results = [",".join(map(str, row)) for row in rows]
                header_str = ",".join(columns)
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        logger.exception("Failed to query table '%s'", table_name)
        return f"查询出现异常：{str(e)}"


@tool
def execute_sql_query(query: str) -> str:
    """
    执行自定义查询 SQL 语句。执行之前需先调用 list_sql_tables 和 get_table_data
    明确表结构。仅允许 SELECT 查询。

    Args:
        query: 要执行的自定义 SQL 语句 (SELECT only)

    Returns:
        CSV 格式数据
    """
    monitor.report_tool(
        tool_name="数据库表数据查询工具：execute_sql_query",
        args={"query": query},
    )

    query_stripped = query.strip().upper()
    if not query_stripped.startswith("SELECT"):
        return "错误：只允许执行 SELECT 查询，当前查询类型被拒绝"

    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                description = cursor.description
                if not description:
                    return f"执行自定义 SQL 语句查询没有结果，sql 为：{query}"
                columns = [desc[0] for desc in description]
                rows = cursor.fetchall()
                results = [",".join(map(str, row)) for row in rows]
                header_str = ",".join(columns)
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        logger.exception("Failed to execute query: %s", query)
        return f"查询出现异常：{str(e)}"
