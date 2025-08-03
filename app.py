from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import time
from dotenv import load_dotenv
from utils import ClashConfigManager
import re
from subscription_parser import SubscriptionParser

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化配置管理器
config_manager = ClashConfigManager()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/urls', methods=['GET'])
def get_saved_urls():
    """获取保存的 URL 历史"""
    try:
        urls = config_manager.load_saved_urls()
        return jsonify({'success': True, 'urls': urls})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-urls', methods=['POST'])
def test_urls():
    """测试 URL 是否可用"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/extract-urls', methods=['POST'])
def extract_urls():
    """从文本中提取 URL"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        # URL 正则表达式
        url_pattern = r'https?://[^\s<>"{}|\\^\[\]`]+'
        urls = re.findall(url_pattern, text)
        
        # 去重
        urls = list(set(urls))
        
        return jsonify({'success': True, 'urls': urls})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/fetch-proxies', methods=['POST'])
def fetch_proxies():
    """从 URL 获取并过滤代理节点"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/parse-clash-nodes', methods=['POST'])
def parse_clash_nodes():
    """解析用户粘贴的 Clash 格式节点"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chained-proxy-config', methods=['GET'])
def get_chained_proxy_config():
    """获取保存的链式代理配置"""
    try:
        config = config_manager.load_chained_proxy_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chained-proxy-config', methods=['POST'])
def save_chained_proxy_config():
    """保存链式代理配置"""
    try:
        data = request.get_json()
        config = data.get('config', {})
        
        config_manager.save_chained_proxy_config(config)
        
        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate-config', methods=['POST'])
def generate_config():
    """生成最终配置并上传到 Gist"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    try:
        config = {
            'github_token': bool(os.getenv('GITHUB_TOKEN')),
            'reuse_gist': os.getenv('REUSE_GIST', 'false').lower() == 'true',
            'has_gist_id': os.path.exists('.gist_id'),
            'default_gist_name': os.getenv('DEFAULT_GIST_NAME')
        }
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gists', methods=['GET'])
def get_gists():
    """获取所有 Gist 配置列表"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gists', methods=['POST'])
def add_gist():
    """添加新的 Gist 配置"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gists/<string:name>', methods=['PUT'])
def update_gist(name):
    """更新 Gist 配置（重命名）"""
    try:
        data = request.get_json()
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({'success': False, 'error': '请提供新名称'})
            
        if config_manager.update_gist_name(name, new_name):
            return jsonify({'success': True, 'message': f'成功将 "{name}" 重命名为 "{new_name}"'})
        else:
            return jsonify({'success': False, 'error': '重命名失败，请检查名称是否存在或新名称是否已被使用'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gists/<string:name>', methods=['DELETE'])
def delete_gist(name):
    """删除 Gist 配置"""
    try:
        # 防止删除最后一个 Gist
        gists = config_manager.load_gist_configs()
        if len(gists) <= 1:
            return jsonify({'success': False, 'error': '不能删除最后一个 Gist 配置'})
            
        if config_manager.remove_gist_config(name):
            return jsonify({'success': True, 'message': f'成功删除 Gist "{name}"'})
        else:
            return jsonify({'success': False, 'error': f'Gist "{name}" 不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/current-gist', methods=['GET'])
def get_current_gist():
    """获取当前选中的 Gist"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)