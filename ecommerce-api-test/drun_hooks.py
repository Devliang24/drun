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


# ==================== Teardown数据清理Hooks（正确用法）====================
# teardown_hooks应该用于数据处理（清理、释放资源），而不是断言

def teardown_hook_cleanup_test_user(
    response: dict,
    variables: dict = None,
    env: dict = None
):
    """清理测试用户数据
    用途：数据清理（teardown的正确用法）
    """
    user_id = variables.get('user_id') if variables else None
    if not user_id:
        return
    
    try:
        proxy = _get_db_proxy()
        # 删除测试用户
        proxy.execute(f"DELETE FROM users WHERE id={user_id}")
        print(f"✅ 已清理测试用户: user_id={user_id}")
    except Exception as e:
        print(f"⚠️ 清理用户失败: {e}")


def teardown_hook_cleanup_test_order(
    response: dict,
    variables: dict = None,
    env: dict = None
):
    """清理测试订单数据
    用途：数据清理（teardown的正确用法）
    """
    order_id = variables.get('order_id') if variables else None
    if not order_id:
        return
    
    try:
        proxy = _get_db_proxy()
        # 先删除订单项
        proxy.execute(f"DELETE FROM order_items WHERE order_id={order_id}")
        # 再删除订单
        proxy.execute(f"DELETE FROM orders WHERE id={order_id}")
        print(f"✅ 已清理测试订单: order_id={order_id}")
    except Exception as e:
        print(f"⚠️ 清理订单失败: {e}")


def teardown_hook_record_test_stats(
    response: dict,
    variables: dict = None,
    env: dict = None
):
    """记录测试统计信息
    用途：数据记录（teardown的正确用法）
    """
    status_code = response.get('status_code')
    elapsed = response.get('elapsed_ms')
    print(f"📊 响应统计: status={status_code}, 耗时={elapsed}ms")


# ==================== 规范的SQL查询Hook函数 ====================
# 每个函数对应一个具体的SQL查询，SQL语句封装在函数内部

# ========== 用户相关SQL查询 ==========

def hook_query_user_username(user_id: int) -> str:
    """从数据库查询用户名
    SQL: SELECT username FROM users WHERE id={user_id}
    """
    try:
        proxy = _get_db_proxy()
        result = proxy.query(f"SELECT username FROM users WHERE id={user_id}")
        print(f"🔍 hook_query_user_username({user_id}): result={result}, type={type(result)}")
        # proxy.query()返回列表，取第一条记录
        if result and isinstance(result, list) and len(result) > 0:
            username = result[0].get('username', '')
            print(f"✅ Found username: {username}")
            return username
        elif result and isinstance(result, dict):
            username = result.get('username', '')
            print(f"✅ Found username (dict): {username}")
            return username
        print(f"⚠️ No result found for user_id={user_id}")
        return ''
    except Exception as e:
        print(f"❌ Hook error in hook_query_user_username({user_id}): {e}")
        # 抛出异常而不是静默返回空字符串
        raise


def hook_query_user_email(user_id: int) -> str:
    """从数据库查询用户邮箱
    SQL: SELECT email FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT email FROM users WHERE id={user_id}")
    # proxy.query()返回列表，取第一条记录
    if result and isinstance(result, list) and len(result) > 0:
        return result[0].get('email', '')
    elif result and isinstance(result, dict):
        return result.get('email', '')
    return ''


def hook_query_user_role(user_id: int) -> str:
    """从数据库查询用户角色
    SQL: SELECT role FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT role FROM users WHERE id={user_id}")
    # proxy.query()返回列表，取第一条记录
    if result and isinstance(result, list) and len(result) > 0:
        return result[0].get('role', '')
    elif result and isinstance(result, dict):
        return result.get('role', '')
    return ''


def hook_query_user_full_name(user_id: int) -> str:
    """从数据库查询用户全名
    SQL: SELECT full_name FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT full_name FROM users WHERE id={user_id}")
    # proxy.query()返回列表，取第一条记录
    if result and isinstance(result, list) and len(result) > 0:
        return result[0].get('full_name', '')
    elif result and isinstance(result, dict):
        return result.get('full_name', '')
    return ''


def hook_query_user_shipping_address(user_id: int) -> str:
    """从数据库查询用户收货地址
    SQL: SELECT shipping_address FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT shipping_address FROM users WHERE id={user_id}")
    # proxy.query()返回列表，取第一条记录
    if result and isinstance(result, list) and len(result) > 0:
        return result[0].get('shipping_address', '')
    elif result and isinstance(result, dict):
        return result.get('shipping_address', '')
    return ''


# ========== 商品相关SQL查询 ==========

def hook_query_product_name(product_id: int) -> str:
    """从数据库查询商品名称
    SQL: SELECT name FROM products WHERE id={product_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT name FROM products WHERE id={product_id}")
    return result.get('name') if result else None


def hook_query_product_stock(product_id: int) -> int:
    """从数据库查询商品库存
    SQL: SELECT stock FROM products WHERE id={product_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT stock FROM products WHERE id={product_id}")
    return result.get('stock') if result else None


def hook_query_product_price(product_id: int) -> float:
    """从数据库查询商品价格
    SQL: SELECT price FROM products WHERE id={product_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT price FROM products WHERE id={product_id}")
    return float(result.get('price')) if result else None


def hook_query_product_description(product_id: int) -> str:
    """从数据库查询商品描述
    SQL: SELECT description FROM products WHERE id={product_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT description FROM products WHERE id={product_id}")
    return result.get('description') if result else None


# ========== 订单相关SQL查询 ==========

def hook_query_order_status(order_id: int) -> str:
    """从数据库查询订单状态
    SQL: SELECT status FROM orders WHERE id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT status FROM orders WHERE id={order_id}")
    return result.get('status') if result else None


def hook_query_order_total_price(order_id: int) -> float:
    """从数据库查询订单总价
    SQL: SELECT total_price FROM orders WHERE id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT total_price FROM orders WHERE id={order_id}")
    return float(result.get('total_price')) if result else None


def hook_query_order_shipping_address(order_id: int) -> str:
    """从数据库查询订单收货地址
    SQL: SELECT shipping_address FROM orders WHERE id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT shipping_address FROM orders WHERE id={order_id}")
    return result.get('shipping_address') if result else None


def hook_query_order_owner_id(order_id: int) -> int:
    """从数据库查询订单所属用户ID
    SQL: SELECT owner_id FROM orders WHERE id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT owner_id FROM orders WHERE id={order_id}")
    return result.get('owner_id') if result else None


# ========== 订单项相关SQL查询 ==========

def hook_query_order_item_quantity(order_id: int) -> int:
    """从数据库查询订单项数量（第一项）
    SQL: SELECT quantity FROM order_items WHERE order_id={order_id} LIMIT 1
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT quantity FROM order_items WHERE order_id={order_id} LIMIT 1")
    return result.get('quantity') if result else None


def hook_query_order_item_product_id(order_id: int) -> int:
    """从数据库查询订单项商品ID（第一项）
    SQL: SELECT product_id FROM order_items WHERE order_id={order_id} LIMIT 1
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT product_id FROM order_items WHERE order_id={order_id} LIMIT 1")
    return result.get('product_id') if result else None


def hook_query_order_item_price(order_id: int) -> float:
    """从数据库查询订单项价格（第一项）
    SQL: SELECT price_at_purchase FROM order_items WHERE order_id={order_id} LIMIT 1
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT price_at_purchase FROM order_items WHERE order_id={order_id} LIMIT 1")
    return float(result.get('price_at_purchase')) if result else None


# ========== 聚合查询SQL ==========

def hook_query_order_total_calculated(order_id: int) -> float:
    """从数据库计算订单总额（SUM）
    SQL: SELECT SUM(price_at_purchase * quantity) as total FROM order_items WHERE order_id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT SUM(price_at_purchase * quantity) as total FROM order_items WHERE order_id={order_id}")
    return float(result.get('total')) if result and result.get('total') else None


def hook_query_user_order_count(user_id: int) -> int:
    """从数据库查询用户订单数量
    SQL: SELECT COUNT(*) as count FROM orders WHERE owner_id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT COUNT(*) as count FROM orders WHERE owner_id={user_id}")
    return result.get('count') if result else 0


# ========== Setup前置准备Hook（不断言） ==========

def setup_hook_prepare_user_data(user_id: int):
    """准备用户测试数据（setup的正确用法）
    用途：前置准备，不断言
    SQL: SELECT id FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT id FROM users WHERE id={user_id}")
    if result:
        print(f"✅ 用户数据已准备: user_id={user_id}")
    else:
        print(f"⚠️ 用户不存在: user_id={user_id}")
    # ❌ 不在setup中断言


def setup_hook_prepare_product_data(product_id: int):
    """准备商品测试数据（setup的正确用法）
    用途：前置准备，不断言
    SQL: SELECT id FROM products WHERE id={product_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT id FROM products WHERE id={product_id}")
    if result:
        print(f"✅ 商品数据已准备: product_id={product_id}")
    else:
        print(f"⚠️ 商品不存在: product_id={product_id}")
    # ❌ 不在setup中断言


def setup_hook_prepare_order_data(order_id: int):
    """准备订单测试数据（setup的正确用法）
    用途：前置准备，不断言
    SQL: SELECT id FROM orders WHERE id={order_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT id FROM orders WHERE id={order_id}")
    if result:
        print(f"✅ 订单数据已准备: order_id={order_id}")
    else:
        print(f"⚠️ 订单不存在: order_id={order_id}")
    # ❌ 不在setup中断言


def setup_hook_create_test_data():
    """创建测试数据（setup的正确用法）
    用途：前置准备测试环境
    """
    print("📦 准备测试数据...")
    # 可以在这里插入测试数据
    # ❌ 不在setup中断言
