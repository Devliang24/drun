"""
Drun Hooks 示例文件

此文件包含可在测试用例中使用的自定义函数：
1. 模板辅助函数：在 ${} 表达式中调用，用于生成数据
2. 生命周期 Hooks：在 setup_hooks/teardown_hooks 中使用

使用方法：
- 模板函数: ${ts()}, ${uid()}, ${md5($password)}
- Hooks 函数: setup_hooks: [${setup_hook_sign_request($request)}]
"""
import hashlib
import hmac
import time
import uuid
from typing import Any

from drun.db.database_proxy import get_db


# ==================== 模板辅助函数 ====================

def ts() -> int:
    """返回当前 Unix 时间戳（秒）

    用法: ${ts()}
    示例: headers: { X-Timestamp: ${ts()} }
    """
    return int(time.time())


def uid() -> str:
    """生成完整的 UUID（带连字符）

    用法: ${uid()}
    示例: email: user_${uid()}@example.com
    """
    return str(uuid.uuid4())


def short_uid(length: int = 8) -> str:
    """生成短 UUID（去除连字符，截取指定长度）

    参数:
        length: 返回的字符串长度（默认 8）

    用法: ${short_uid(12)}
    示例: username: user_${short_uid(8)}
    """
    return str(uuid.uuid4()).replace("-", "")[:length]


def md5(text: str) -> str:
    """计算字符串的 MD5 哈希值

    用法: ${md5($password)}
    示例: headers: { X-Sign: ${md5($timestamp + $secret)} }
    """
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def sha256(text: str) -> str:
    """计算字符串的 SHA256 哈希值

    用法: ${sha256($data)}
    """
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


# ==================== 生命周期 Hooks ====================

def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """请求签名 Hook 示例：添加 HMAC-SHA256 签名

    此 Hook 会：
    1. 生成当前时间戳
    2. 使用 APP_SECRET 对请求进行签名
    3. 添加 X-Timestamp 和 X-Signature 头

    使用方法:
        steps:
          - name: 调用需要签名的接口
            setup_hooks:
              - ${setup_hook_sign_request($request)}
            request:
              method: POST
              path: /api/secure/endpoint

    参数:
        request: 当前请求对象（方法、URL、headers 等）
        variables: 当前会话变量
        env: 环境变量

    返回:
        dict: 返回的变量会注入到当前步骤的变量作用域
    """
    env = env or {}
    secret = env.get("APP_SECRET", "default-secret-key").encode()

    method = request.get("method", "GET")
    url = request.get("url", "")
    timestamp = str(int(time.time()))

    # 计算签名：HMAC-SHA256(method|url|timestamp)
    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    # 添加签名相关的 headers
    headers = request.setdefault("headers", {})
    headers["X-Timestamp"] = timestamp
    headers["X-Signature"] = signature

    # 可选：返回签名信息供后续步骤使用
    return {
        "last_signature": signature,
        "last_timestamp": timestamp,
    }


def teardown_hook_log_response(response: dict, variables: dict = None, env: dict = None):
    """响应日志 Hook 示例：记录响应关键信息

    使用方法:
        steps:
          - name: 创建订单
            teardown_hooks:
              - ${teardown_hook_log_response($response)}

    参数:
        response: 响应对象（status_code、body 等）
        variables: 当前会话变量
        env: 环境变量
    """
    status = response.get("status_code")
    body = response.get("body", {})

    # 可以在这里添加自定义日志逻辑
    print(f"[Hook] Response: status={status}, body_keys={list(body.keys() if isinstance(body, dict) else [])}")


def teardown_hook_validate_status(response: dict, variables: dict = None, env: dict = None):
    """响应验证 Hook 示例：确保状态码为 2xx

    使用方法:
        steps:
          - name: 调用接口
            teardown_hooks:
              - ${teardown_hook_validate_status($response)}
    """
    status = response.get("status_code", 0)
    if not (200 <= status < 300):
        raise AssertionError(f"Expected 2xx status code, got {status}")


# ==================== 数据库辅助函数 ====================

def _get_db_proxy(db_name: str = "main", role: str | None = None):
    """内部工具：按库名/角色获取数据库代理。"""
    manager = get_db()
    return manager.get(db_name, role)


def setup_hook_assert_sql(
    identifier: Any,
    *,
    query: str | None = None,
    db_name: str = "main",
    role: str | None = None,
    fail_message: str | None = None,
) -> dict:
    """在步骤前执行 SQL 并判空，常用于校验前置数据是否存在。

    用法:
        setup_hooks:
          - ${setup_hook_assert_sql($variables.user_id)}
        # 指定数据库角色或自定义 SQL:
        # - ${setup_hook_assert_sql($user_id, query="SELECT * FROM users WHERE id=${user_id}", db_name="analytics", role="read")}

    返回:
        dict: 默认返回 `{"sql_assert_ok": True}`，可用于在后续步骤判断断言是否执行。
    """
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query
    if sql is None:
        try:
            uid = int(identifier)
            sql = f"SELECT id, status FROM users WHERE id = {uid}"
        except (TypeError, ValueError):
            sql = f"SELECT id, status FROM users WHERE id = '{identifier}'"
    row = proxy.query(sql)
    if not row:
        message = fail_message or f"SQL 返回为空，无法继续执行：{sql}"
        raise AssertionError(message)
    # 返回标记，后续步骤如果需要可判断
    return {"sql_assert_ok": True}


def expected_sql_value(
    identifier: Any,
    *,
    query: str | None = None,
    column: str = "status",
    db_name: str = "main",
    role: str | None = None,
    default: Any | None = None,
) -> Any:
    """在 validate 断言中调用，返回 SQL 查询的指定列值。

    用法:
        validate:
          - eq: [$api_status, ${expected_sql_value($api_user_id)}]
        # 自定义 SQL 与列名:
          - eq: [$.data.total, ${expected_sql_value($order_id, query="SELECT SUM(amount) AS total FROM orders WHERE order_id=${order_id}", column="total", db_name="report")}]
    """
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query
    if sql is None:
        try:
            uid = int(identifier)
            sql = f"SELECT {column} FROM users WHERE id = {uid}"
        except (TypeError, ValueError):
            sql = f"SELECT {column} FROM users WHERE id = '{identifier}'"
    row = proxy.query(sql)
    if not row:
        if default is not None:
            return default
        raise AssertionError(f"SQL 返回为空，无法获取列 {column}: {sql}")
    if column not in row:
        raise AssertionError(f"SQL 结果缺少列 {column}: {row.keys()}")
    return row[column]


# ==================== Suite 级别 Hooks ====================

def suite_setup():
    """Suite 开始前的准备工作

    使用方法（在测试套件中）:
        config:
          setup_hooks:
            - ${suite_setup()}
    """
    print("[Suite Hook] Suite setup: 准备测试环境...")
    # 可以在这里执行：
    # - 清理测试数据库
    # - 初始化测试数据
    # - 启动 mock 服务
    return {}


def suite_teardown():
    """Suite 结束后的清理工作

    使用方法（在测试套件中）:
        config:
          teardown_hooks:
            - ${suite_teardown()}
    """
    print("[Suite Hook] Suite teardown: 清理测试环境...")
    # 可以在这里执行：
    # - 清理测试数据
    # - 停止 mock 服务
    # - 生成额外报告


def case_setup():
    """Case 开始前的准备工作

    使用方法（在测试用例中）:
        config:
          setup_hooks:
            - ${case_setup()}
    """
    print("[Case Hook] Case setup: 准备用例数据...")
    return {}


def case_teardown():
    """Case 结束后的清理工作

    使用方法（在测试用例中）:
        config:
          teardown_hooks:
            - ${case_teardown()}
    """
    print("[Case Hook] Case teardown: 清理用例数据...")
