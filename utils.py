import os
import json
import requests
import yaml
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from subscription_parser import SubscriptionParser
from urllib.parse import urlparse


class ClashConfigManager:
    """管理 Clash 配置的核心类"""
    
    # 地区关键词映射
    REGION_KEYWORDS = {
        'hk': ['香港', 'hk', 'hongkong', 'hong kong', '🇭🇰', 'HK', 'HongKong', 'Hong Kong'],
        'tw': ['台湾', 'tw', 'taiwan', '🇹🇼', 'TW', 'Taiwan', '台北', 'taipei'],
        'us': ['美国', 'us', 'usa', 'united states', '🇺🇸', 'US', 'USA', 'America', '美國'],
        'sg': ['新加坡', 'sg', 'singapore', '🇸🇬', 'SG', 'Singapore', '狮城']
    }
    
    # 常见订阅服务的友好名称映射
    KNOWN_SERVICES = {
        'zlsub': 'ZL订阅',
        'isufe': 'ISUFE订阅',
        'xn--cp3a08l': '订阅服务',
        'baiqiandao': '百千道订阅',
        '52pokemon': '52Pokemon订阅'
    }
    
    def __init__(self):
        self.gist_id_file = '.gist_id'
        self.urls_file = 'data/urls.json'
        self.template_file = 'example.yaml'
        self.chained_config_file = 'data/chained_proxy_config.json'
        self._gist_configs = None  # 缓存 Gist 配置
        
    def _read_json_file(self, file_path: str, default_value=None):
        """通用JSON文件读取函数"""
        if not os.path.exists(file_path):
            return default_value if default_value is not None else {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default_value if default_value is not None else {}
            
    def _write_json_file(self, file_path: str, data: dict, ensure_dir: bool = True):
        """通用JSON文件写入函数"""
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
    def _migrate_url_data(self, data: dict) -> dict:
        """迁移旧版本URL数据到新格式"""
        # 检查是否是旧格式（没有version字段或urls是字符串列表）
        if 'version' not in data or (isinstance(data.get('urls', []), list) and
                                    len(data.get('urls', [])) > 0 and
                                    isinstance(data.get('urls', [])[0], str)):
            # 迁移到新格式
            old_urls = data.get('urls', [])
            new_urls = []
            for url in old_urls:
                new_urls.append({
                    'url': url,
                    'alias': self.generate_default_alias(url),
                    'auto_alias': self.generate_default_alias(url),
                    'added_at': data.get('updated', datetime.now().isoformat())
                })
            
            return {
                'version': '2.0',
                'urls': new_urls,
                'updated': data.get('updated', datetime.now().isoformat())
            }
        return data
    
    def generate_default_alias(self, url: str) -> str:
        """生成URL的默认别名"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 移除常见的前缀
            domain = domain.replace('www.', '')
            
            # 检查是否是已知服务
            for key, friendly_name in self.KNOWN_SERVICES.items():
                if key in domain:
                    return friendly_name
            
            # 提取主域名部分
            parts = domain.split('.')
            if len(parts) >= 2:
                # 取主域名部分
                main_domain = parts[0]
                # 限制长度
                if len(main_domain) > 15:
                    main_domain = main_domain[:15] + '...'
                return f"{main_domain}订阅"
            else:
                return f"{domain[:20]}订阅"
                
        except Exception:
            # 如果解析失败，使用URL的一部分
            return f"订阅_{url[:20]}..."
        
    def load_saved_urls(self) -> List[Dict[str, str]]:
        """加载保存的 URL 历史（新格式）"""
        data = self._read_json_file(self.urls_file, {'version': '2.0', 'urls': []})
        # 迁移旧数据
        data = self._migrate_url_data(data)
        return data.get('urls', [])
    
    def load_saved_urls_simple(self) -> List[str]:
        """加载保存的 URL 历史（仅返回URL字符串列表，用于兼容）"""
        urls_data = self.load_saved_urls()
        return [item['url'] for item in urls_data]
        
    def save_urls(self, urls: List[str]):
        """保存 URL 到历史记录"""
        existing_data = self.load_saved_urls()
        existing_url_map = {item['url']: item for item in existing_data}
        
        # 处理新URL
        for url in urls:
            if url not in existing_url_map:
                # 新URL，生成默认别名
                alias = self.generate_default_alias(url)
                existing_url_map[url] = {
                    'url': url,
                    'alias': alias,
                    'auto_alias': alias,
                    'added_at': datetime.now().isoformat()
                }
        
        # 转换回列表
        all_urls = list(existing_url_map.values())
        
        data = {
            'version': '2.0',
            'urls': all_urls,
            'updated': datetime.now().isoformat()
        }
        self._write_json_file(self.urls_file, data)
        
    def delete_url(self, url: str) -> bool:
        """从历史记录中删除指定的URL
        
        Args:
            url: 要删除的URL
            
        Returns:
            是否删除成功
        """
        existing_data = self.load_saved_urls()
        
        # 找到并删除对应的URL
        original_length = len(existing_data)
        existing_data = [item for item in existing_data if item['url'] != url]
        
        if len(existing_data) < original_length:
            data = {
                'version': '2.0',
                'urls': existing_data,
                'updated': datetime.now().isoformat()
            }
            self._write_json_file(self.urls_file, data)
            return True
        return False
    
    def update_url_alias(self, url: str, new_alias: str) -> bool:
        """更新URL的别名
        
        Args:
            url: URL地址
            new_alias: 新的别名
            
        Returns:
            是否更新成功
        """
        existing_data = self.load_saved_urls()
        
        for item in existing_data:
            if item['url'] == url:
                item['alias'] = new_alias
                data = {
                    'version': '2.0',
                    'urls': existing_data,
                    'updated': datetime.now().isoformat()
                }
                self._write_json_file(self.urls_file, data)
                return True
        return False
            
    def test_url_availability(self, url: str) -> Tuple[bool, str]:
        """测试 URL 是否可用"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                return True, "可用"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "超时"
        except requests.exceptions.ConnectionError:
            return False, "连接错误"
        except Exception as e:
            return False, str(e)
            
    def fetch_and_parse_subscription(self, url: str) -> List[Dict[str, Any]]:
        """获取并解析订阅内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            content = response.text
            return SubscriptionParser.parse_subscription(content)
        except Exception as e:
            raise Exception(f"获取订阅失败: {str(e)}")
            
    def filter_proxies(self, proxies: List[Dict[str, Any]], filter_options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据过滤选项过滤代理节点
        
        Args:
            proxies: 代理节点列表
            filter_options: 过滤选项，可包含：
                - regions: List[str] - 地区列表，如 ['hk', 'tw']，'all' 表示所有
                - keywords: List[str] - 自定义关键词列表
        """
        regions = filter_options.get('regions', [])
        keywords = filter_options.get('keywords', [])
        
        # 如果选择了 'all'，返回所有节点
        if 'all' in regions:
            return proxies
            
        filtered_nodes = []
        
        # 收集所有需要匹配的关键词
        all_keywords = []
        
        # 添加地区关键词
        for region in regions:
            if region in self.REGION_KEYWORDS:
                all_keywords.extend(self.REGION_KEYWORDS[region])
                
        # 添加自定义关键词
        all_keywords.extend(keywords)
        
        # 如果没有任何关键词，返回空列表
        if not all_keywords:
            return []
            
        # 过滤节点
        for proxy in proxies:
            if isinstance(proxy, dict) and 'name' in proxy:
                name = proxy['name'].lower()
                if any(kw.lower() in name for kw in all_keywords):
                    filtered_nodes.append(proxy)
                    
        return filtered_nodes
        
    def load_chained_proxy_config(self) -> Dict[str, Any]:
        """加载链式代理配置"""
        default_config = {
            'version': '1.0',
            'updated': datetime.now().isoformat(),
            'custom_nodes': [],  # 用户手动添加的节点
            'chained_nodes': {},  # {node_id: dialer_proxy_name} 映射
        }
        return self._read_json_file(self.chained_config_file, default_config)
        
    def save_chained_proxy_config(self, config: Dict[str, Any]):
        """保存链式代理配置"""
        # 清理无效的引用
        config = self._clean_chained_config(config)
        config['updated'] = datetime.now().isoformat()
        self._write_json_file(self.chained_config_file, config)
            
    def apply_dialer_proxy_config(self, nodes: List[Dict[str, Any]], chained_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """为节点应用 dialer-proxy 配置
        
        Args:
            nodes: 节点列表
            chained_config: {node_id: dialer_proxy_name} 映射
            
        Returns:
            应用了 dialer-proxy 配置的节点列表
        """
        for node in nodes:
            node_id = node.get('_id', '')
            if node_id in chained_config:
                node['dialer-proxy'] = chained_config[node_id]
        return nodes
        
    def _clean_chained_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清理链式代理配置中的无效引用
        
        Args:
            config: 包含 custom_nodes, chained_nodes, selected_proxy_ids 等的配置
            
        Returns:
            清理后的配置
        """
        # 收集所有有效的节点ID
        valid_ids = set()
        
        # 从 all_proxies 收集ID
        for proxy in config.get('all_proxies', []):
            if '_id' in proxy:
                valid_ids.add(proxy['_id'])
                
        # 从 custom_nodes 收集ID
        for node in config.get('custom_nodes', []):
            if '_id' in node:
                valid_ids.add(node['_id'])
        
        # 清理 chained_nodes - 只保留存在的节点的链式代理配置
        old_chained = config.get('chained_nodes', {})
        cleaned_chained = {}
        for node_id, dialer in old_chained.items():
            if node_id in valid_ids:
                cleaned_chained[node_id] = dialer
        config['chained_nodes'] = cleaned_chained
        
        # 清理 selected_proxy_ids - 只保留存在的节点ID
        old_selected = config.get('selected_proxy_ids', [])
        cleaned_selected = []
        for proxy_id in old_selected:
            if proxy_id in valid_ids:
                cleaned_selected.append(proxy_id)
        config['selected_proxy_ids'] = cleaned_selected
        
        # 记录清理信息（用于调试）
        removed_chained = len(old_chained) - len(cleaned_chained)
        removed_selected = len(old_selected) - len(cleaned_selected)
        if removed_chained > 0 or removed_selected > 0:
            print(f"清理了 {removed_chained} 个无效的链式代理配置，{removed_selected} 个无效的选中节点ID")
        
        return config
        
    def _format_yaml_value(self, key: str, value: Any) -> Optional[str]:
        """格式化 YAML 值"""
        if value is None:
            return None
            
        if isinstance(value, str):
            # 字符串值需要引号
            if any(char in value for char in [':', '{', '}', '"', '\n', '#']):
                # 对包含特殊字符的字符串使用双引号
                escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                return f'{key}: "{escaped_value}"'
            else:
                return f'{key}: "{value}"'
        elif isinstance(value, bool):
            # 布尔值转换为小写
            return f'{key}: {str(value).lower()}'
        elif isinstance(value, (int, float)):
            # 数字直接转换
            return f'{key}: {value}'
        elif isinstance(value, list):
            # 列表转换为 YAML 数组格式
            return f'{key}: [{", ".join(str(item) for item in value)}]'
        elif isinstance(value, dict):
            # 字典转换为内联格式
            dict_items = []
            for k, v in value.items():
                if isinstance(v, str):
                    dict_items.append(f'{k}: "{v}"')
                else:
                    dict_items.append(f'{k}: {v}')
            return f'{key}: {{ {", ".join(dict_items)} }}'
        else:
            # 其他类型尝试直接转换
            return f'{key}: {value}'
            
    def _escape_for_yaml_regex(self, name: str) -> str:
        """为 YAML 中的正则表达式智能转义节点名称
        
        Args:
            name: 节点名称
            
        Returns:
            转义后的名称，适用于 YAML 双引号字符串中的正则表达式
        """
        # 定义需要在正则表达式中转义的特殊字符
        # 注意：这里只包含真正需要转义的字符
        regex_special_chars = {
            '.': True,  # 匹配任意字符
            '^': True,  # 行首
            '$': True,  # 行尾
            '*': True,  # 零次或多次
            '+': True,  # 一次或多次
            '?': True,  # 零次或一次
            '{': True,  # 量词开始
            '}': True,  # 量词结束
            '[': True,  # 字符类开始
            ']': True,  # 字符类结束
            '(': True,  # 分组开始
            ')': True,  # 分组结束
            '|': True,  # 或操作
            '\\': True, # 反斜杠本身
            # 注意：- 在字符类外部不是特殊字符，不需要转义
        }
        
        escaped = ""
        for char in name:
            if char in regex_special_chars:
                # 在 YAML 双引号字符串中，反斜杠需要双重转义
                escaped += "\\\\" + char
            else:
                # 普通字符直接添加，不需要转义
                escaped += char
        
        return escaped
        
    def merge_proxies_to_template(self, proxies: List[Dict[str, Any]], chained_config: Dict[str, str] = None) -> str:
        """将代理节点合并到模板中
        
        Args:
            proxies: 代理节点列表
            chained_config: 链式代理配置，用于生成 exclude-filter
        """
        # 读取模板文件
        with open(self.template_file, 'r', encoding='utf-8') as f:
            template_lines = f.readlines()
            
        # 生成代理节点的 YAML 格式
        proxy_yaml_lines = []
        for proxy in proxies:
            # 使用 flow style 生成紧凑的节点格式
            items = []
            
            # 定义字段顺序（重要字段优先）
            field_order = ['name', 'type', 'server', 'port', 'ports', 'mport',
                          'password', 'cipher', 'uuid', 'alterId', 'udp',
                          'skip-cert-verify', 'sni', 'dialer-proxy']
            
            # 首先按照定义的顺序添加字段
            for key in field_order:
                if key in proxy and not key.startswith('_'):
                    value = proxy[key]
                    formatted_value = self._format_yaml_value(key, value)
                    if formatted_value:
                        items.append(formatted_value)
            
            # 然后添加其他未在顺序中定义的字段
            for key, value in proxy.items():
                if key not in field_order and not key.startswith('_'):
                    formatted_value = self._format_yaml_value(key, value)
                    if formatted_value:
                        items.append(formatted_value)
            
            # 构建节点行
            proxy_line = '  - { ' + ', '.join(items) + ' }'
            proxy_yaml_lines.append(proxy_line)
            
        # 如果有链式代理配置，收集需要排除的节点名称
        exclude_names = []
        if chained_config:
            for proxy in proxies:
                if proxy.get('_id') in chained_config and 'dialer-proxy' in proxy:
                    # 对节点名称进行智能转义
                    name = proxy.get('name', '')
                    # 使用智能转义，避免YAML解析错误
                    escaped_name = self._escape_for_yaml_regex(name)
                    exclude_names.append(escaped_name)
        
        # 查找需要插入节点的位置
        result_lines = []
        i = 0
        proxies_added = False
        
        while i < len(template_lines):
            line = template_lines[i]
            
            # 检查是否是 exclude-filter 行
            if 'exclude-filter:' in line and exclude_names:
                # 生成新的 exclude-filter 行
                exclude_pattern = '|'.join(exclude_names)
                # 保持原有的缩进
                indent = line[:len(line) - len(line.lstrip())]
                new_line = f'{indent}exclude-filter: "{exclude_pattern}"\n'
                result_lines.append(new_line)
                # 调试信息
                print(f"[DEBUG] Generated exclude-filter: {new_line.strip()}")
            else:
                result_lines.append(line)
            
            # 检查是否是 proxies: 行
            if line.strip() == 'proxies:' and not proxies_added:
                # 检查下一行是否有 # 添加处 注释
                if i + 1 < len(template_lines) and '# 添加处' in template_lines[i + 1]:
                    # 保留注释行
                    i += 1
                    result_lines.append(template_lines[i])
                    
                    # 添加新的代理节点
                    for proxy_line in proxy_yaml_lines:
                        result_lines.append(proxy_line + '\n')
                    
                    # 标记已添加，避免在其他 proxies: 处重复添加
                    proxies_added = True
                    
                    # 跳过原有的代理节点（如果有）
                    i += 1
                    while i < len(template_lines):
                        current_line = template_lines[i]
                        # 如果遇到非缩进行（新的顶层配置项）或空行，停止跳过
                        if current_line.strip() and not current_line.startswith(' '):
                            i -= 1  # 回退一行，让外层循环处理这一行
                            break
                        if not current_line.strip():  # 空行
                            i -= 1  # 回退一行，让外层循环处理这一行
                            break
                        i += 1
            
            i += 1
            
        return ''.join(result_lines)
        
    def load_gist_configs(self) -> Dict[str, str]:
        """加载所有 Gist 配置
        
        Returns:
            {name: gist_id} 字典
        """
        if self._gist_configs is not None:
            return self._gist_configs
            
        configs = {}
        
        if os.path.exists(self.gist_id_file):
            try:
                with open(self.gist_id_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # 处理旧格式（单行 gist_id）
                if len(lines) == 1 and ':' not in lines[0]:
                    gist_id = lines[0].strip()
                    if gist_id:
                        configs['默认'] = gist_id
                        # 自动转换为新格式
                        self.save_gist_configs(configs)
                else:
                    # 新格式（名称:gist_id）
                    for line in lines:
                        line = line.strip()
                        if line and ':' in line:
                            name, gist_id = line.split(':', 1)
                            configs[name.strip()] = gist_id.strip()
            except Exception as e:
                print(f"加载 Gist 配置失败: {e}")
                
        self._gist_configs = configs
        return configs
        
    def save_gist_configs(self, configs: Dict[str, str]):
        """保存 Gist 配置
        
        Args:
            configs: {name: gist_id} 字典
        """
        lines = []
        for name, gist_id in configs.items():
            lines.append(f"{name}:{gist_id}\n")
            
        with open(self.gist_id_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        self._gist_configs = configs
        
    def get_gist_id(self, name: str = None) -> Optional[str]:
        """根据名称获取 Gist ID
        
        Args:
            name: Gist 名称，如果为 None 则使用默认
            
        Returns:
            Gist ID 或 None
        """
        configs = self.load_gist_configs()
        
        if not configs:
            return None
            
        # 如果指定了名称，直接返回
        if name:
            return configs.get(name)
            
        # 检查环境变量中的默认名称
        default_name = os.getenv('DEFAULT_GIST_NAME')
        if default_name and default_name in configs:
            return configs[default_name]
            
        # 返回第一个
        return list(configs.values())[0]
        
    def add_gist_config(self, name: str, gist_id: str):
        """添加新的 Gist 配置
        
        Args:
            name: Gist 名称
            gist_id: Gist ID
        """
        configs = self.load_gist_configs()
        configs[name] = gist_id
        self.save_gist_configs(configs)
        
    def remove_gist_config(self, name: str) -> bool:
        """删除 Gist 配置
        
        Args:
            name: Gist 名称
            
        Returns:
            是否删除成功
        """
        configs = self.load_gist_configs()
        if name in configs:
            del configs[name]
            self.save_gist_configs(configs)
            return True
        return False
        
    def update_gist_name(self, old_name: str, new_name: str) -> bool:
        """重命名 Gist
        
        Args:
            old_name: 旧名称
            new_name: 新名称
            
        Returns:
            是否重命名成功
        """
        configs = self.load_gist_configs()
        if old_name in configs and new_name not in configs:
            configs[new_name] = configs[old_name]
            del configs[old_name]
            self.save_gist_configs(configs)
            return True
        return False
        
    def upload_to_gist(self, content: str, github_token: str, reuse_gist: bool = False, gist_name: str = None) -> tuple:
        """上传内容到 GitHub Gist"""
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 检查是否需要重用 Gist
        gist_id = None
        if reuse_gist:
            gist_id = self.get_gist_id(gist_name)
                
        try:
            if gist_id and reuse_gist:
                # 更新现有 Gist
                data = {
                    'description': f'Clash Config - Updated {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                    'files': {
                        'clash_config.yaml': {
                            'content': content
                        }
                    }
                }
                
                response = requests.patch(
                    f'https://api.github.com/gists/{gist_id}',
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
            else:
                # 创建新 Gist
                data = {
                    'description': f'Clash Config - {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                    'public': False,
                    'files': {
                        'clash_config.yaml': {
                            'content': content
                        }
                    }
                }
                
                response = requests.post(
                    'https://api.github.com/gists',
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                
                # 保存新创建的 Gist ID
                new_gist_id = response.json()['id']
                
                # 确定 Gist 名称
                if not gist_name:
                    # 如果没有指定名称，使用自动命名格式
                    gist_name = f"Clash配置_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 添加到配置中
                self.add_gist_config(gist_name, new_gist_id)
            
            gist_data = response.json()
            raw_url = gist_data['files']['clash_config.yaml']['raw_url']
            
            # 如果启用了重用，返回永久链接（去掉 commit SHA）
            if reuse_gist:
                # 从 raw_url 中提取必要部分，构建永久链接
                # 原始: .../raw/commit_sha/filename
                # 永久: .../raw/filename
                parts = raw_url.split('/raw/')
                if len(parts) == 2:
                    base_url = parts[0]
                    filename = parts[1].split('/')[-1]  # 获取文件名
                    raw_url = f"{base_url}/raw/{filename}"
            
            return raw_url, gist_name
        except Exception as e:
            raise Exception(f"上传 Gist 失败: {str(e)}")
            
    def fetch_proxies_from_urls(self, urls: List[str], filter_options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """从 URL 列表获取并过滤代理节点
        
        Args:
            urls: 订阅 URL 列表
            filter_options: 过滤选项
            
        Returns:
            过滤后的代理节点列表
        """
        if filter_options is None:
            filter_options = {'regions': ['hk']}  # 默认过滤香港节点
            
        # 保存 URL 到历史
        self.save_urls(urls)
        
        all_proxies = []
        details = []
        
        for url in urls:
            detail = {'url': url, 'status': '', 'total_nodes': 0, 'filtered_nodes': 0}
            
            # 测试 URL 可用性
            is_available, status_msg = self.test_url_availability(url)
            detail['status'] = status_msg
            
            if is_available:
                try:
                    proxies = self.fetch_and_parse_subscription(url)
                    detail['total_nodes'] = len(proxies)
                    
                    # 过滤节点
                    filtered = self.filter_proxies(proxies, filter_options)
                    all_proxies.extend(filtered)
                    detail['filtered_nodes'] = len(filtered)
                except Exception as e:
                    detail['status'] = f"解析失败: {str(e)}"
                    
            details.append(detail)
            
        # 为每个节点添加唯一 ID，方便前端追踪
        for i, proxy in enumerate(all_proxies):
            proxy['_id'] = f"proxy_{i}"
            
        return all_proxies
        
    def generate_config_from_proxies(self,
                                   selected_proxies: List[Dict[str, Any]],
                                   custom_nodes: List[Dict[str, Any]] = None,
                                   chained_config: Dict[str, str] = None,
                                   github_token: str = None,
                                   reuse_gist: bool = False,
                                   save_config: bool = True,
                                   gist_name: str = None) -> Dict[str, Any]:
        """根据选择的代理节点生成配置
        
        Args:
            selected_proxies: 用户选择的代理节点
            custom_nodes: 用户手动添加的节点
            chained_config: {node_id: dialer_proxy_name} 映射
            github_token: GitHub Token
            reuse_gist: 是否重用 Gist
            save_config: 是否保存配置到本地
            gist_name: 指定使用的 Gist 名称
            
        Returns:
            包含结果的字典
        """
        result = {
            'success': False,
            'message': '',
            'subscription_url': ''
        }
        
        try:
            if custom_nodes is None:
                custom_nodes = []
            if chained_config is None:
                chained_config = {}
                
            # 收集所有有效节点的ID
            valid_node_ids = set()
            for proxy in selected_proxies:
                if '_id' in proxy:
                    valid_node_ids.add(proxy['_id'])
            for node in custom_nodes:
                if '_id' in node:
                    valid_node_ids.add(node['_id'])
                    
            # 清理 chained_config，只保留有效节点的配置
            cleaned_chained_config = {}
            for node_id, dialer in chained_config.items():
                if node_id in valid_node_ids:
                    cleaned_chained_config[node_id] = dialer
                    
            # 应用 dialer-proxy 配置
            selected_proxies = self.apply_dialer_proxy_config(selected_proxies, cleaned_chained_config)
            custom_nodes = self.apply_dialer_proxy_config(custom_nodes, cleaned_chained_config)
            
            # 合并所有节点
            all_nodes = selected_proxies + custom_nodes
            
            # 对节点进行排序：链式代理节点在前，自定义节点次之，普通节点在后
            def sort_key(node):
                is_chained = node.get('_id', '') in cleaned_chained_config
                is_custom = node.get('is_custom', False)
                
                # 返回元组用于排序：(链式代理优先级, 自定义节点优先级)
                # 数字越小，优先级越高
                if is_chained:
                    return (0, 0 if is_custom else 1)  # 链式代理最优先，其中自定义的更优先
                elif is_custom:
                    return (1, 0)  # 非链式的自定义节点次之
                else:
                    return (2, 0)  # 普通节点最后
            
            all_nodes.sort(key=sort_key)
            
            if not all_nodes:
                result['message'] = "没有任何节点需要处理"
                return result
                
            # 保存配置到本地
            if save_config:
                config = self.load_chained_proxy_config()
                config['custom_nodes'] = custom_nodes
                config['chained_nodes'] = cleaned_chained_config  # 使用清理后的配置
                # 保存所有代理节点和选中的节点ID（用于后续清理）
                config['all_proxies'] = selected_proxies
                config['selected_proxy_ids'] = [p['_id'] for p in all_nodes if '_id' in p]
                self.save_chained_proxy_config(config)
                
            # 生成配置
            merged_config = self.merge_proxies_to_template(all_nodes, cleaned_chained_config)
            
            # 上传到 Gist
            gist_url, actual_gist_name = self.upload_to_gist(merged_config, github_token, reuse_gist, gist_name)
            
            result['success'] = True
            result['message'] = f"成功生成配置，包含 {len(all_nodes)} 个节点"
            result['subscription_url'] = gist_url
            result['gist_name'] = actual_gist_name  # 返回实际使用的 Gist 名称
            result['reuse_gist'] = reuse_gist  # 返回是否重用了现有 Gist
            result['details'] = {
                'total_nodes': len(all_nodes),
                'selected_nodes': len(selected_proxies),
                'custom_nodes': len(custom_nodes),
                'chained_nodes': len([n for n in all_nodes if 'dialer-proxy' in n])
            }
            
            return result
            
        except Exception as e:
            result['message'] = str(e)
            return result