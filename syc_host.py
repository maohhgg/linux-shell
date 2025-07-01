import os
import json
import requests
import http.cookiejar as cookielib
import pickle
import redis
import logging

from datetime import datetime, timezone
from urllib.parse import quote
from pathlib import Path

def is_cookie_expired(session, url):
    """
    检查指定URL的cookie是否已过期
    
    参数:
    session (requests.Session): 会话对象
    url (str): 目标URL
    
    返回:
    bool: 如果cookie已过期返回True，否则返回False
    """
    if not session.cookies:
        return True
    
    domain = requests.utils.urlparse(url).netloc
    
    # 检查所有关联的cookie是否过期
    now = datetime.now(timezone.utc)
    for cookie in session.cookies:
        # 如果cookie有过期时间且已过期
        if cookie.expires and datetime.fromtimestamp(cookie.expires, timezone.utc) < now:
            return True
                
    return False

def login_and_get_cookie(login_url, payload, redis_client, cookie_key, headers=None, expire_time=86400):
    """
    模拟登录指定URL，获取并保存cookie到Redis
    
    参数:
    login_url (str): 登录接口URL
    payload (dict): 登录所需的表单数据
    redis_client (redis.Redis): Redis客户端实例
    cookie_key (str): 存储在Redis中的cookie键名
    headers (dict, optional): HTTP请求头
    expire_time (int, optional): Redis中cookie的过期时间（秒），默认为1天
    
    返回:
    requests.Session: 已登录的会话对象
    """
    # 创建会话
    session = requests.Session()
    
    # 如果需要自定义请求头
    if headers:
        session.headers.update(headers)
    
    # 尝试从Redis获取cookie
    cookie_data = redis_client.get(cookie_key)
    if cookie_data:
        try:
            # 反序列化cookie数据
            cookies_dict = pickle.loads(cookie_data)
            # 将cookie字典加载到会话中
            session.cookies.update(cookies_dict)
            
            # 如果cookie没有过期，则直接返回会话
            if not is_cookie_expired(session, login_url):
                return session
        except Exception as e:
            # 如果出现异常，继续执行登录流程
            pass

    # 发送登录请求
    try:
        response = session.post(login_url, data=payload)
        response.raise_for_status()  # 检查请求是否成功
        
        # 将cookie保存到Redis
        cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
        redis_client.set(cookie_key, pickle.dumps(cookies_dict), ex=expire_time)
        
        return session
    
    except requests.exceptions.RequestException as e:
        return None

def use_cookie_to_access(url, session, headers=None, data=None):
    """
    使用已登录的会话访问受保护的URL
    
    参数:
    url (str): 要访问的URL
    session (requests.Session): 已登录的会话对象
    
    返回:
    str: 响应内容
    """
    if not session:
        return None
    
    try:
        # 如果需要自定义请求头
        if headers:
            session.headers.update(headers)
        if data:
            response = session.post(url, data=data)
        else:
            response = session.post(url)
        response.raise_for_status()

        # 检查响应内容是否为空
        if not response.text.strip():
            raise ValueError("服务器返回了空响应")
            
        try:
            content = json.loads(response.text)
            if content['success']:
                return content
            raise ValueError(content['msg'])
        except json.JSONDecodeError as e:
            # 记录原始响应内容以便调试
            print(f"JSON解析错误: {e}")
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}")
            raise ValueError(f"无法解析JSON响应: {e}, 响应内容: {response.text[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return None
    except Exception as e:
        print(f"访问URL时发生错误: {e}")
        raise

# 配置日志记录
def setup_logger(log_file='syc.log'):
    """
    配置日志记录器
    
    参数:
    log_file (str): 日志文件路径
    
    返回:
    logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger('syc')
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_data(logger, action, data):
    """
    记录关键数据到日志
    
    参数:
    logger (logging.Logger): 日志记录器
    action (str): 操作类型
    data: 要记录的数据
    """
    if isinstance(data, (dict, list)):
        logger.info(f"{action}: {json.dumps(data, ensure_ascii=False)}")
    else:
        logger.info(f"{action}: {data}")


def main():
    # 设置日志记录器
    logger = setup_logger()

    BASE_DIR = Path.cwd()

    HOSTS = "127.0.0.1:2053"
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None  # 如果Redis需要密码，请在这里设置
    COOKIE_KEY = "syc_cookies"  # Redis中存储cookie的键名
    ONLINES_KEY = "syc_onlines"  # Redis中存储onlines的键名

    # 用于出口的反向客户端
    ALL_OUTBINDS = ["hostip", "docker"]
    # 实际使用的客户端
    USERS = ["home_ip", "ss_home_ip"]
    
    # 接口URL
    URLS = {
        "LOGIN": "login",
        "ONLINE_CLIENT": "panel/api/inbounds/onlines",
        "SERVER_RESTART": "server/restartXrayService",
        "SERVER_CONFIG": "panel/xray",
        "CONFIG_UPDATE": "panel/xray/update"
    }
    
    # 登录表单数据
    PAYLOAD = {
        "username": "pi",
        "password": "debian"
    }
    
    # 可选的请求头
    HEADERS = {
        "Accept-Language": "zh-CN,zh;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    # 创建Redis客户端
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=False  # 不要解码响应，因为我们存储的是二进制数据
        )
    except Exception as e:
        logger.error(f"Redis客户端创建失败: {e}")
        return
    
    # 执行登录并获取cookie
    try:
        session = login_and_get_cookie(
            f"http://{HOSTS}/{URLS['LOGIN']}", 
            PAYLOAD, 
            redis_client, 
            COOKIE_KEY, 
            headers=HEADERS
        )
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return
    
    # 使用获取的cookie访问受保护的URL
    if not session:
        logger.error("会话无效，无法继续")
        return
        
    try:
        outbinds_response = use_cookie_to_access(f"http://{HOSTS}/{URLS['ONLINE_CLIENT']}", session, headers=HEADERS)
        outbinds = outbinds_response['obj']
        
        onlines = list(set(ALL_OUTBINDS) & set(outbinds))
    except Exception as e:
        logger.error(f"获取在线节点失败: {e}")
        return
    
    # 从Redis获取之前保存的onlines
    prev_onlines = []
    try:
        prev_onlines_data = redis_client.get(ONLINES_KEY)
        if prev_onlines_data:
            prev_onlines = pickle.loads(prev_onlines_data)
    except Exception as e:
        logger.error(f"从Redis加载onlines失败: {e}")

    # 保存当前onlines到Redis
    try:
        redis_client.set(ONLINES_KEY, pickle.dumps(onlines), ex=86400)  # 设置过期时间为1天
    except Exception as e:
        logger.error(f"保存onlines到Redis失败: {e}")
    
    # 计算节点上线和下线的差异
    if prev_onlines:
        # 新上线的节点（当前onlines中有，但prev_onlines中没有）
        new_online_nodes = set(onlines) - set(prev_onlines)
        if new_online_nodes:
            log_data(logger, "上线节点：", list(new_online_nodes))
        
        # 新下线的节点（prev_onlines中有，但当前onlines中没有）
        new_offline_nodes = set(prev_onlines) - set(onlines)
        if new_offline_nodes:
            log_data(logger, "下线节点：", list(new_offline_nodes))
    
    # 比较当前onlines和之前的onlines是否相同
    if prev_onlines and set(prev_onlines) == set(onlines):
        return

    if len(onlines) == len(ALL_OUTBINDS):
        return
    
    
    # 获取服务器配置
    try:
        config_response = use_cookie_to_access(f"http://{HOSTS}/{URLS['SERVER_CONFIG']}", session, headers=HEADERS)
        config = json.loads(config_response['obj'])["xraySetting"]
    except Exception as e:
        logger.error(f"获取服务器配置失败: {e}")
        return
    
    # 更新路由规则
    try:
        rules = []
        lists = config["routing"]["rules"]
        for rule in lists:
            if rule["outboundTag"] not in ALL_OUTBINDS or "domain" in rule:
                rules.append(rule)
        
        new_rule = {
            "user": USERS,
            "outboundTag": onlines[0],
            "inboundTag": [ "inbound-35833","inbound-443"],
            "type": "field"
        }
        rules.append(new_rule)
        log_data(logger, "流量承载节点：", onlines[0])
        
        config["routing"]["rules"] = rules
        xraySetting = {
            "xraySetting": json.dumps(config, indent=2) 
        }
    except Exception as e:
        logger.error(f"更新路由规则失败: {e}")
        return

    # 更新配置并重启服务
    try:
        update_response = use_cookie_to_access(
            f"http://{HOSTS}/{URLS['CONFIG_UPDATE']}", 
            session, 
            data=xraySetting, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        restart_response = use_cookie_to_access(f"http://{HOSTS}/{URLS['SERVER_RESTART']}", session, headers=HEADERS)

        if not update_response or not restart_response:
            logger.error("配置更新或服务重启失败")
            return

    except Exception as e:
        logger.error(f"配置更新或服务重启失败: {e}")


if __name__ == "__main__":
    main()

        
