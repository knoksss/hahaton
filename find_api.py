# find_api.py
import requests
import json

def test_endpoints():
    base_url = "https://affine.ml-dev.scibox.tech"
    
    # Различные возможные пути API
    endpoints = [
        # Стандартные OpenAI-совместимые пути
        "/v1/chat/completions",
        "/api/v1/chat/completions", 
        "/chat/completions",
        "/api/chat/completions",
        
        # Возможные пути для affine
        "/api/chat",
        "/api/completions",
        "/api/generate",
        "/api/v1/generate",
        "/api/v1/completions",
        
        # Пути с workspace ID
        "/workspace/61d6d8eb-6e83-4978-9d0d-37d439046c04/api/chat",
        "/workspace/61d6d8eb-6e83-4978-9d0d-37d439046c04/api/completions",
        "/workspace/61d6d8eb-6e83-4978-9d0d-37d439046c04/api/v1/chat/completions",
        "/workspace/61d6d8eb-6e83-4978-9d0d-37d439046c04/chat/completions",
        
        # Другие возможные варианты
        "/gateway/chat/completions",
        "/proxy/v1/chat/completions",
        "/v1/completions",
        "/api",
        "/chat"
    ]
    
    test_message = {
        "model": "qwen3-32b-awq",
        "messages": [{"role": "user", "content": "Hello, respond with just 'OK'"}],
        "temperature": 0.7,
        "max_tokens": 10
    }
    
    # Попробуйте разные токены
    tokens_to_try = [
        "sk-1234",  # ваш текущий токен
        "test",
        "demo", 
        "affine",
        ""  # пустой токен
    ]
    
    working_endpoints = []
    
    for token in tokens_to_try:
        headers = {
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        print(f"\n🔐 Testing with token: '{token}'")
        print("=" * 50)
        
        for endpoint in endpoints:
            try:
                url = base_url + endpoint
                print(f"🔍 Testing: {url}")
                
                response = requests.post(url, headers=headers, json=test_message, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ SUCCESS! Working endpoint found!")
                    working_endpoints.append({
                        'url': url,
                        'token': token,
                        'response': response.json() if response.text else 'Empty response'
                    })
                    try:
                        result = response.json()
                        print(f"   Response: {result}")
                    except:
                        print(f"   Response: {response.text[:200]}")
                elif response.status_code == 404:
                    print("   ❌ 404 - Not Found")
                elif response.status_code == 401:
                    print("   🔐 401 - Unauthorized")
                elif response.status_code == 403:
                    print("   🚫 403 - Forbidden")
                elif response.status_code == 400:
                    print("   📝 400 - Bad Request")
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Response: {response.text[:200]}")
                else:
                    print(f"   ⚠️  {response.status_code}")
                    print(f"   Response: {response.text[:100]}")
                    
            except requests.exceptions.ConnectionError:
                print("   🔌 Connection Error")
            except requests.exceptions.Timeout:
                print("   ⏰ Timeout")
            except Exception as e:
                print(f"   💥 Error: {e}")
            
            print()
    
    return working_endpoints

def test_get_requests():
    """Тестируем GET запросы чтобы понять структуру API"""
    base_url = "https://affine.ml-dev.scibox.tech"
    
    get_endpoints = [
        "/",
        "/api",
        "/api/v1/models",
        "/v1/models", 
        "/models",
        "/api/models",
        "/health",
        "/status",
        "/docs",
        "/swagger",
        "/openapi.json"
    ]
    
    tokens_to_try = ["sk-1234", "test", "demo", ""]
    
    print("\n🔍 Testing GET endpoints...")
    print("=" * 50)
    
    for token in tokens_to_try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        print(f"\n🔐 Token: '{token}'")
        
        for endpoint in get_endpoints:
            try:
                url = base_url + endpoint
                print(f"   Testing GET: {url}")
                
                response = requests.get(url, headers=headers, timeout=5)
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("      ✅ 200 OK")
                    try:
                        data = response.json()
                        print(f"      Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except:
                        print(f"      Response: {response.text[:500]}...")
                elif response.status_code in [301, 302]:
                    print(f"      🔀 Redirect to: {response.headers.get('Location', 'Unknown')}")
                else:
                    print(f"      Response: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"      Error: {e}")
    
    return []

if __name__ == "__main__":
    print("🚀 Starting comprehensive API endpoint discovery...")
    print("This will test multiple endpoints and authentication tokens")
    print("=" * 60)
    
    # Тестируем POST endpoints
    working_post = test_endpoints()
    
    # Тестируем GET endpoints
    working_get = test_get_requests()
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print("🎯 DISCOVERY RESULTS:")
    print("=" * 60)
    
    if working_post:
        print(f"✅ Found {len(working_post)} working POST endpoints:")
        for i, endpoint in enumerate(working_post, 1):
            print(f"   {i}. URL: {endpoint['url']}")
            print(f"      Token: '{endpoint['token']}'")
            print(f"      Response: {endpoint['response']}")
    else:
        print("❌ No working POST endpoints found")
    
    print("\n💡 RECOMMENDATIONS:")
    if working_post:
        print("   Use one of the working endpoints above in your app.py configuration")
    else:
        print("   1. Check if the affine service is running")
        print("   2. Look for API documentation")
        print("   3. Check network requests in browser developer tools")
        print("   4. Try different authentication tokens")
        print("   5. Contact the affine service administrator")