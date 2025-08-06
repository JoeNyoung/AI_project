# check_environment.py
"""
프로젝트 실행 전 환경 설정 검증
"""
import os
import sys
from pathlib import Path

def check_python_version():
    """Python 버전 확인"""
    version = sys.version_info
    print(f"🐍 Python 버전: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        return False
    else:
        print("✅ Python 버전 OK")
        return True

def check_required_packages():
    """필수 패키지 설치 확인"""
    required_packages = [
        "openai", "requests", "beautifulsoup4", "pandas", 
        "langchain", "langchain_openai", "faiss", "streamlit",
        "python-dotenv", "langdetect", "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "faiss":
                import faiss
            elif package == "langchain_openai":
                import langchain_openai
            elif package == "python-dotenv":
                import dotenv
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    else:
        print("✅ 모든 필수 패키지 설치됨")
        return True

def check_env_file():
    """환경변수 파일 확인"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env 파일이 없습니다.")
        print("다음 내용으로 .env 파일을 생성하세요:")
        print("OPENAI_API_KEY=your_openai_api_key_here")
        return False
    
    # .env 파일 내용 확인
    env_content = env_file.read_text()
    
    if "OPENAI_API_KEY" not in env_content:
        print("❌ .env 파일에 OPENAI_API_KEY가 없습니다.")
        return False
    
    # API 키 값 확인
    for line in env_content.split('\n'):
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.split('=', 1)[1].strip()
            if not api_key or api_key == 'your_openai_api_key_here':
                print("❌ OPENAI_API_KEY 값이 설정되지 않았습니다.")
                return False
            else:
                print("✅ .env 파일 및 API 키 설정됨")
                return True
    
    return False

def check_openai_connection():
    """OpenAI API 연결 테스트"""
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("❌ OPENAI_API_KEY 환경변수가 없습니다.")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # 간단한 API 호출 테스트
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ OpenAI API 연결 성공")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API 연결 실패: {e}")
        return False

def check_directory_structure():
    """디렉토리 구조 확인"""
    required_files = [
        "config.py", "crawler_utils.py", "analyzer.py", 
        "prompts.py", "category_mapper.py", "vector_store.py",
        "rag_chain.py", "streamlit_app.py"
    ]
    
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
            print(f"❌ {file}")
        else:
            print(f"✅ {file}")
    
    if missing_files:
        print(f"\n📁 누락된 파일: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 모든 필수 파일 존재")
        return True

def create_directories():
    """필요한 디렉토리 생성"""
    directories = ["logs", "data", "vector_store"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ {directory}/ 디렉토리 준비됨")

def main():
    """환경 검증 메인 함수"""
    print("🔍 환경 설정 검증 시작...\n")
    
    checks = [
        ("Python 버전", check_python_version),
        ("필수 패키지", check_required_packages),
        ("환경변수 파일", check_env_file),
        ("파일 구조", check_directory_structure),
        ("OpenAI API", check_openai_connection),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"🧪 {check_name} 확인")
        print('='*50)
        
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} 확인 중 오류: {e}")
            all_passed = False
    
    print(f"\n{'='*50}")
    print("📁 디렉토리 생성")
    print('='*50)
    create_directories()
    
    print(f"\n{'='*80}")
    if all_passed:
        print("🎉 모든 환경 설정이 완료되었습니다!")
        print("다음 명령어로 전체 파이프라인을 실행하세요:")
        print("  python pipeline_full.py")
        print("또는 단계별 실행:")
        print("  1. python main.py  # 크롤링")
        print("  2. python run_embedding_update.py  # 분석 및 벡터화")
        print("  3. streamlit run streamlit_app.py  # 웹 UI 실행")
    else:
        print("❌ 환경 설정에 문제가 있습니다.")
        print("위의 오류들을 해결한 후 다시 실행해주세요.")
    print("="*80)

if __name__ == "__main__":
    main()
    