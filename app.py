from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from utils import ClashConfigManager
from subscription_parser import SubscriptionParser
from functools import wraps

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化配置管理器
config_manager = ClashConfigManager()

# 错误处理装饰器
def handle_api_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return decorated_function

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/urls', methods=['GET'])
@handle_api_errors
def get_saved_urls():
    """获取保存的 URL 历史（包含别名）"""
    urls_data = config_manager.load_saved_urls()
    return jsonify({'success': True, 'urls': urls_data})

@app.route('/api/urls/<path:url>', methods=['DELETE'])
@handle_api_errors
def delete_url(url):
    """删除指定的 URL 历史"""
    import urllib.parse
    
    # URL 解码
    decoded_url = urllib.parse.unquote(url)
    
    if config_manager.delete_url(decoded_url):
        return jsonify({'success': True, 'message': 'URL 已删除'})
    else:
        return jsonify({'success': False, 'error': 'URL 不存在'})

@app.route('/api/urls/<path:url>/alias', methods=['PUT'])
@handle_api_errors
def update_url_alias(url):
    """更新URL的别名"""
    import urllib.parse
    
    # URL 解码
    decoded_url = urllib.parse.unquote(url)
    
    data = request.get_json()
    new_alias = data.get('alias', '').strip()
    
    if not new_alias:
        return jsonify({'success': False, 'error': '别名不能为空'})
    
    if config_manager.update_url_alias(decoded_url, new_alias):
        return jsonify({'success': True, 'message': '别名已更新'})
    else:
        return jsonify({'success': False, 'error': 'URL 不存在'})

@app.route('/api/test-urls', methods=['POST'])
@handle_api_errors
def test_urls():
    """测试 URL 是否可用"""
    data = request.get_json()
    urls = data.get('urls', [])
    
    results = []
    for url in urls:
        is_available, status = config_manager.test_url_availability(url)
        results.append({
            'url': url,
            'available': is_available,
            'status': status
        })
        
    return jsonify({'success': True, 'results': results})

@app.route('/api/extract-urls', methods=['POST'])
@handle_api_errors
def extract_urls():
    """从文本中提取 URL"""
    import re  # 按需导入
    
    data = request.get_json()
    text = data.get('text', '')
    include_aliases = data.get('include_aliases', False)
    
    # URL 正则表达式
    url_pattern = r'https?://[^\s<>"{}|\\^\[\]`]+'
    urls = re.findall(url_pattern, text)
    
    # 去重
    urls = list(set(urls))
    
    # 如果需要包含别名信息
    if include_aliases:
        urls_with_aliases = []
        for url in urls:
            alias = config_manager.generate_default_alias(url)
            urls_with_aliases.append({
                'url': url,
                'alias': alias
            })
        return jsonify({'success': True, 'urls': urls_with_aliases})
    
    return jsonify({'success': True, 'urls': urls})

@app.route('/api/fetch-proxies', methods=['POST'])
@handle_api_errors
def fetch_proxies():
    """从 URL 获取并过滤代理节点"""
    data = request.get_json()
    urls = data.get('urls', [])
    filter_options = data.get('filter_options', {'regions': ['hk']})
    
    if not urls:
        return jsonify({'success': False, 'error': '请提供至少一个订阅 URL'})
        
    # 获取并过滤节点
    proxies = config_manager.fetch_proxies_from_urls(urls, filter_options)
    
    return jsonify({
        'success': True,
        'proxies': proxies,
        'total': len(proxies)
    })

@app.route('/api/parse-clash-nodes', methods=['POST'])
@handle_api_errors
def parse_clash_nodes():
    """解析用户粘贴的 Clash 格式节点"""
    import time  # 按需导入
    
    data = request.get_json()
    nodes_text = data.get('nodes_text', '')
    
    if not nodes_text.strip():
        return jsonify({'success': False, 'error': '请输入节点配置'})
        
    # 使用 SubscriptionParser 解析节点
    nodes = SubscriptionParser.parse_clash_nodes(nodes_text)
    
    # 为每个节点添加唯一 ID 和标记
    for i, node in enumerate(nodes):
        node['_id'] = f"custom_{i}_{int(time.time())}"
        node['is_custom'] = True
        
    return jsonify({
        'success': True,
        'nodes': nodes,
        'total': len(nodes)
    })

@app.route('/api/chained-proxy-config', methods=['GET'])
@handle_api_errors
def get_chained_proxy_config():
    """获取保存的链式代理配置"""
    config = config_manager.load_chained_proxy_config()
    return jsonify({'success': True, 'config': config})

@app.route('/api/chained-proxy-config', methods=['POST'])
@handle_api_errors
def save_chained_proxy_config():
    """保存链式代理配置"""
    data = request.get_json()
    config = data.get('config', {})
    
    config_manager.save_chained_proxy_config(config)
    
    return jsonify({'success': True, 'message': '配置已保存'})

@app.route('/api/generate-config', methods=['POST'])
@handle_api_errors
def generate_config():
    """生成最终配置并上传到 Gist"""
    data = request.get_json()
    selected_proxies = data.get('selected_proxies', [])
    custom_nodes = data.get('custom_nodes', [])
    chained_config = data.get('chained_config', {})
    save_config = data.get('save_config', True)
    gist_name = data.get('gist_name')  # 新增：指定使用的 Gist
    
    # 获取 GitHub Token
    github_token = data.get('github_token') or os.getenv('GITHUB_TOKEN')
    if not github_token:
        return jsonify({'success': False, 'error': '请提供 GitHub Token'})
        
    # 获取是否重用 Gist
    reuse_gist = data.get('reuse_gist', os.getenv('REUSE_GIST', 'false').lower() == 'true')
    
    # 生成配置
    result = config_manager.generate_config_from_proxies(
        selected_proxies=selected_proxies,
        custom_nodes=custom_nodes,
        chained_config=chained_config,
        github_token=github_token,
        reuse_gist=reuse_gist,
        save_config=save_config,
        gist_name=gist_name
    )
    
    return jsonify(result)

@app.route('/api/config', methods=['GET'])
@handle_api_errors
def get_config():
    """获取当前配置"""
    config = {
        'github_token': bool(os.getenv('GITHUB_TOKEN')),
        'reuse_gist': os.getenv('REUSE_GIST', 'false').lower() == 'true',
        'has_gist_id': os.path.exists('.gist_id'),
        'default_gist_name': os.getenv('DEFAULT_GIST_NAME')
    }
    return jsonify({'success': True, 'config': config})

@app.route('/api/gists', methods=['GET'])
@handle_api_errors
def get_gists():
    """获取所有 Gist 配置列表"""
    gists = config_manager.load_gist_configs()
    
    # 转换为列表格式，便于前端使用
    gist_list = []
    for name, gist_id in gists.items():
        gist_list.append({
            'name': name,
            'id': gist_id,
            'is_default': name == os.getenv('DEFAULT_GIST_NAME')
        })
        
    return jsonify({
        'success': True,
        'gists': gist_list,
        'default_name': os.getenv('DEFAULT_GIST_NAME')
    })

@app.route('/api/gists', methods=['POST'])
@handle_api_errors
def add_gist():
    """添加新的 Gist 配置"""
    data = request.get_json()
    name = data.get('name')
    gist_id = data.get('gist_id', '')  # 可选，如果为空则在生成时创建
    
    if not name:
        return jsonify({'success': False, 'error': '请提供 Gist 名称'})
        
    # 检查名称是否已存在
    gists = config_manager.load_gist_configs()
    if name in gists:
        return jsonify({'success': False, 'error': f'名称 "{name}" 已存在'})
        
    # 如果提供了 gist_id，则添加；否则先添加空值，后续生成时更新
    config_manager.add_gist_config(name, gist_id)
    
    return jsonify({'success': True, 'message': f'成功添加 Gist "{name}"'})

@app.route('/api/gists/<string:name>', methods=['PUT'])
@handle_api_errors
def update_gist(name):
    """更新 Gist 配置（重命名）"""
    data = request.get_json()
    new_name = data.get('new_name')
    
    if not new_name:
        return jsonify({'success': False, 'error': '请提供新名称'})
        
    if config_manager.update_gist_name(name, new_name):
        return jsonify({'success': True, 'message': f'成功将 "{name}" 重命名为 "{new_name}"'})
    else:
        return jsonify({'success': False, 'error': '重命名失败，请检查名称是否存在或新名称是否已被使用'})

@app.route('/api/gists/<string:name>', methods=['DELETE'])
@handle_api_errors
def delete_gist(name):
    """删除 Gist 配置"""
    # 防止删除最后一个 Gist
    gists = config_manager.load_gist_configs()
    if len(gists) <= 1:
        return jsonify({'success': False, 'error': '不能删除最后一个 Gist 配置'})
        
    if config_manager.remove_gist_config(name):
        return jsonify({'success': True, 'message': f'成功删除 Gist "{name}"'})
    else:
        return jsonify({'success': False, 'error': f'Gist "{name}" 不存在'})

@app.route('/api/current-gist', methods=['GET'])
@handle_api_errors
def get_current_gist():
    """获取当前选中的 Gist"""
    # 这个端点主要用于前端获取当前应该使用哪个 Gist
    default_name = os.getenv('DEFAULT_GIST_NAME')
    gists = config_manager.load_gist_configs()
    
    # 如果有默认名称且存在，返回它
    if default_name and default_name in gists:
        current_name = default_name
    else:
        # 否则返回第一个
        current_name = list(gists.keys())[0] if gists else None
        
    return jsonify({
        'success': True,
        'current_name': current_name,
        'current_id': gists.get(current_name) if current_name else None
    })

@app.route('/api/save-github-token', methods=['POST'])
@handle_api_errors
def save_github_token():
    """保存 GitHub Token 到 .env 文件"""
    data = request.get_json()
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({'success': False, 'error': '请提供有效的 GitHub Token'})
    
    # 读取现有的 .env 文件内容
    env_file = '.env'
    env_lines = []
    token_exists = False
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
    
    # 更新或添加 GITHUB_TOKEN
    for i, line in enumerate(env_lines):
        if line.strip().startswith('GITHUB_TOKEN='):
            env_lines[i] = f'GITHUB_TOKEN={token}\n'
            token_exists = True
            break
    
    if not token_exists:
        env_lines.append(f'GITHUB_TOKEN={token}\n')
    
    # 写入 .env 文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(env_lines)
    
    # 更新当前环境变量
    os.environ['GITHUB_TOKEN'] = token
    
    return jsonify({'success': True, 'message': 'GitHub Token 已保存到 .env 文件'})

@app.route('/api/github-token', methods=['GET'])
@handle_api_errors
def get_github_token_status():
    """获取 GitHub Token 状态"""
    # 检查环境变量中是否有 token
    env_token = os.getenv('GITHUB_TOKEN')
    
    if env_token:
        # 隐藏 token，只显示前几位和后几位
        masked_token = f"{env_token[:8]}...{env_token[-4:]}" if len(env_token) > 12 else "***"
        return jsonify({
            'success': True, 
            'has_token': True,
            'source': 'env',
            'masked_token': masked_token
        })
    else:
        return jsonify({
            'success': True, 
            'has_token': False,
            'source': None,
            'masked_token': None
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)