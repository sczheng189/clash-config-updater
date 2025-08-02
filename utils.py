import os
import json
import requests
import yaml
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from subscription_parser import SubscriptionParser


class ClashConfigManager:
    """管理 Clash 配置的核心类"""
    
    # 地区关键词映射
    REGION_KEYWORDS = {
        'hk': ['香港', 'hk', 'hongkong', 'hong kong', '🇭🇰', 'HK', 'HongKong', 'Hong Kong'],
        'tw': ['台湾', 'tw', 'taiwan', '🇹🇼', 'TW', 'Taiwan', '台北', 'taipei'],
        'us': ['美国', 'us', 'usa', 'united states', '🇺🇸', 'US', 'USA', 'America', '美國'],
        'sg': ['新加坡', 'sg', 'singapore', '🇸🇬', 'SG', 'Singapore', '狮城']
    }
    
    def __init__(self):
        self.gist_id_file = '.gist_id'
        self.urls_file = 'data/urls.json'
        self.template_file = 'example.yaml'
        self.chained_config_file = 'data/chained_proxy_config.json'
        
    def load_saved_urls(self) -> List[str]:
        """加载保存的 URL 历史"""
        if os.path.exists(self.urls_file):
            try:
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('urls', [])
            except:
                pass
        return []
        
    def save_urls(self, urls: List[str]):
        """保存 URL 到历史记录"""
        existing_urls = self.load_saved_urls()
        # 合并新旧 URL，去重
        all_urls = list(set(existing_urls + urls))
        
        # 确保目录存在
        os.makedirs('data', exist_ok=True)
        
        with open(self.urls_file, 'w', encoding='utf-8') as f:
            json.dump({'urls': all_urls, 'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
            
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
        if os.path.exists(self.chained_config_file):
            try:
                with open(self.chained_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'version': '1.0',
            'updated': datetime.now().isoformat(),
            'custom_nodes': [],  # 用户手动添加的节点
            'chained_nodes': {},  # {node_id: dialer_proxy_name} 映射
        }
        
    def save_chained_proxy_config(self, config: Dict[str, Any]):
        """保存链式代理配置"""
        config['updated'] = datetime.now().isoformat()
        
        # 确保目录存在
        os.makedirs('data', exist_ok=True)
        
        with open(self.chained_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
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
                    # 对节点名称进行转义，处理特殊字符
                    name = proxy.get('name', '')
                    # 转义正则表达式特殊字符
                    escaped_name = re.escape(name)
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
        
    def upload_to_gist(self, content: str, github_token: str, reuse_gist: bool = False) -> str:
        """上传内容到 GitHub Gist"""
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 检查是否需要重用 Gist
        gist_id = None
        if reuse_gist and os.path.exists(self.gist_id_file):
            try:
                with open(self.gist_id_file, 'r') as f:
                    gist_id = f.read().strip()
            except:
                pass
                
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
                
                # 如果启用了重用，保存 Gist ID
                if reuse_gist:
                    new_gist_id = response.json()['id']
                    with open(self.gist_id_file, 'w') as f:
                        f.write(new_gist_id)
            
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
            
            return raw_url
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
                                   save_config: bool = True) -> Dict[str, Any]:
        """根据选择的代理节点生成配置
        
        Args:
            selected_proxies: 用户选择的代理节点
            custom_nodes: 用户手动添加的节点
            chained_config: {node_id: dialer_proxy_name} 映射
            github_token: GitHub Token
            reuse_gist: 是否重用 Gist
            save_config: 是否保存配置到本地
            
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
                
            # 应用 dialer-proxy 配置
            selected_proxies = self.apply_dialer_proxy_config(selected_proxies, chained_config)
            custom_nodes = self.apply_dialer_proxy_config(custom_nodes, chained_config)
            
            # 合并所有节点
            all_nodes = selected_proxies + custom_nodes
            
            if not all_nodes:
                result['message'] = "没有任何节点需要处理"
                return result
                
            # 保存配置到本地
            if save_config:
                config = self.load_chained_proxy_config()
                config['custom_nodes'] = custom_nodes
                config['chained_nodes'] = chained_config
                self.save_chained_proxy_config(config)
                
            # 生成配置
            merged_config = self.merge_proxies_to_template(all_nodes, chained_config)
            
            # 上传到 Gist
            gist_url = self.upload_to_gist(merged_config, github_token, reuse_gist)
            
            result['success'] = True
            result['message'] = f"成功生成配置，包含 {len(all_nodes)} 个节点"
            result['subscription_url'] = gist_url
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