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
            save_config=save_config
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
            'has_gist_id': os.path.exists('.gist_id')
        }
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)