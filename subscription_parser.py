import base64
import json
import yaml
import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict, Any, Optional
from functools import wraps

def safe_parse(func):
    """解析函数的安全装饰器，统一异常处理"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return None
    return wrapper

class SubscriptionParser:
    """订阅内容解析器"""
    
    @staticmethod
    def parse_subscription(content: str) -> List[Dict[str, Any]]:
        """解析订阅内容，自动识别格式"""
        proxies = []
        
        # 尝试作为 YAML 解析
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
        except:
            pass
            
        # 尝试作为 Base64 解析
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            return SubscriptionParser.parse_subscription(decoded)
        except:
            pass
            
        # 尝试作为分享链接列表解析
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            proxy = None
            if line.startswith('ss://'):
                proxy = SubscriptionParser.parse_ss(line)
            elif line.startswith('vmess://'):
                proxy = SubscriptionParser.parse_vmess(line)
            elif line.startswith('trojan://'):
                proxy = SubscriptionParser.parse_trojan(line)
            elif line.startswith('hysteria2://'):
                proxy = SubscriptionParser.parse_hysteria2(line)
                
            if proxy:
                proxies.append(proxy)
                
        return proxies
        
    @staticmethod
    @safe_parse
    def parse_ss(url: str) -> Optional[Dict[str, Any]]:
        """解析 Shadowsocks 链接"""
        # 移除 ss:// 前缀
        content = url[5:]
        
        # 分离备注
        if '#' in content:
            content, remark = content.split('#', 1)
            remark = unquote(remark)
        else:
            remark = "SS"
            
        # 解析主体部分
        if '@' in content:
            # 新格式: method:password@server:port
            auth, server_info = content.split('@', 1)
            server, port = server_info.split(':', 1)
            
            # 解码认证信息
            try:
                auth = base64.b64decode(auth + '==').decode('utf-8')
            except:
                pass
                
            if ':' in auth:
                method, password = auth.split(':', 1)
            else:
                method = 'aes-256-gcm'
                password = auth
        else:
            # 旧格式: base64(method:password@server:port)
            try:
                decoded = base64.b64decode(content + '==').decode('utf-8')
                auth, server_info = decoded.split('@', 1)
                server, port = server_info.split(':', 1)
                method, password = auth.split(':', 1)
            except:
                return None
                
        return {
            'name': remark,
            'type': 'ss',
            'server': server,
            'port': int(port),
            'cipher': method,
            'password': password,
            'udp': True
        }
            
    @staticmethod
    @safe_parse
    def parse_vmess(url: str) -> Optional[Dict[str, Any]]:
        """解析 VMess 链接"""
        # 移除 vmess:// 前缀
        content = url[8:]
        
        # Base64 解码
        decoded = base64.b64decode(content + '==').decode('utf-8')
        config = json.loads(decoded)
        
        proxy = {
            'name': config.get('ps', 'VMess'),
            'type': 'vmess',
            'server': config.get('add', ''),
            'port': int(config.get('port', 443)),
            'uuid': config.get('id', ''),
            'alterId': int(config.get('aid', 0)),
            'cipher': 'auto',
            'udp': True
        }
        
        # 添加 TLS 配置
        if config.get('tls') == 'tls':
            proxy['tls'] = True
            if config.get('sni'):
                proxy['servername'] = config.get('sni')
                
        # 添加传输层配置
        network = config.get('net', 'tcp')
        if network != 'tcp':
            proxy['network'] = network
            if network == 'ws':
                ws_opts = {}
                if config.get('path'):
                    ws_opts['path'] = config.get('path')
                if config.get('host'):
                    ws_opts['headers'] = {'Host': config.get('host')}
                if ws_opts:
                    proxy['ws-opts'] = ws_opts
                    
        return proxy
            
    @staticmethod
    @safe_parse
    def parse_trojan(url: str) -> Optional[Dict[str, Any]]:
        """解析 Trojan 链接"""
        parsed = urlparse(url)
        
        # 获取备注
        remark = "Trojan"
        if '#' in url:
            remark = unquote(url.split('#')[-1])
            
        proxy = {
            'name': remark,
            'type': 'trojan',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'password': parsed.username,
            'udp': True,
            'skip-cert-verify': True
        }
        
        # 解析查询参数
        params = parse_qs(parsed.query)
        if 'sni' in params:
            proxy['sni'] = params['sni'][0]
            
        return proxy
            
    @staticmethod
    @safe_parse
    def parse_hysteria2(url: str) -> Optional[Dict[str, Any]]:
        """解析 Hysteria2 链接"""
        # 解析 URL
        parsed = urlparse(url)
        
        # 获取备注
        remark = "Hysteria2"
        if '#' in url:
            remark = unquote(url.split('#')[-1])
            
        proxy = {
            'name': remark,
            'type': 'hysteria2',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'password': parsed.username or parsed.password,
            'skip-cert-verify': True
        }
        
        # 解析查询参数
        params = parse_qs(parsed.query)
        if 'sni' in params:
            proxy['sni'] = params['sni'][0]
        if 'insecure' in params and params['insecure'][0] == '1':
            proxy['skip-cert-verify'] = True
            
        return proxy
    
    @staticmethod
    def parse_clash_nodes(content: str) -> List[Dict[str, Any]]:
        """解析用户粘贴的 Clash 格式节点"""
        nodes = []
        
        # 支持多种格式：
        # 1. 完整的 YAML 格式
        # 2. 单行格式: - { name: xxx, ... }
        # 3. 多行格式但没有 proxies: 前缀
        
        content = content.strip()
        
        # 尝试直接作为 YAML 列表解析
        try:
            # 如果内容不是以 - 开头，尝试添加
            if not content.startswith('-'):
                # 可能是 { } 格式，转换为列表格式
                if content.startswith('{'):
                    content = f"- {content}"
            
            parsed = yaml.safe_load(content)
            
            if isinstance(parsed, list):
                nodes = parsed
            elif isinstance(parsed, dict):
                # 单个节点
                nodes = [parsed]
        except:
            # YAML 解析失败，尝试逐行解析
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 尝试解析单行 Clash 节点
                node = SubscriptionParser._parse_clash_line(line)
                if node:
                    nodes.append(node)
        
        return nodes
    
    @staticmethod
    @safe_parse
    def _parse_clash_line(line: str) -> Optional[Dict[str, Any]]:
        """解析单行 Clash 格式节点"""
        line = line.strip()
        
        # 移除开头的 - 符号
        if line.startswith('-'):
            line = line[1:].strip()
        
        # 尝试解析 { } 格式
        if line.startswith('{') and line.endswith('}'):
            # 移除大括号
            content = line[1:-1].strip()
            
            # 解析键值对
            node = {}
            
            # 使用正则表达式解析键值对
            # 支持格式: key: value 或 key: "value"
            pattern = r'(\w+[-\w]*)\s*:\s*([^,]+?)(?:\s*,\s*|\s*$)'
            matches = re.findall(pattern, content)
            
            for key, value in matches:
                # 清理值
                value = value.strip()
                
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # 转换布尔值
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # 转换数字
                elif value.replace('-', '').isdigit():
                    # 处理端口范围，如 20000-50000
                    if '-' in value and not value.startswith('-'):
                        value = value  # 保持字符串格式
                    else:
                        value = int(value)
                # 尝试转换浮点数
                else:
                    try:
                        value = float(value)
                    except:
                        pass  # 保持字符串
                
                node[key] = value
            
            # 确保有必要的字段
            if 'name' in node and 'type' in node and 'server' in node:
                return node
        
        return None