#!/usr/bin/env python3
"""
Script untuk menginstall dlib dengan pre-compiled wheels
dan packages lainnya untuk FastAPI project
"""
import subprocess
import sys
import platform

def get_python_version():
    """Mendapatkan versi Python major.minor"""
    version = sys.version_info
    return f"{version.major}.{version.minor}"

def run_command(command, description=""):
    """Menjalankan command dan handle error"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')[-5:]
                for line in lines:
                    print(f"  {line}")
        else:
            print("❌ ERROR")
            print("STDERR:", result.stderr[-800:])
            return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False
    
    return True

def install_dlib_precompiled():
    """Install dlib menggunakan pre-compiled wheel"""
    python_version = get_python_version()
    print(f"Detected Python version: {python_version}")
    
    # Mapping versi Python ke URL wheel
    wheel_urls = {
        "3.7": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp37-cp37m-win_amd64.whl",
        "3.8": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp38-cp38-win_amd64.whl", 
        "3.9": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp39-cp39-win_amd64.whl",
        "3.10": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp310-cp310-win_amd64.whl",
        "3.11": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp311-cp311-win_amd64.whl",
        "3.12": "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.0-cp312-cp312-win_amd64.whl"
    }
    
    if python_version in wheel_urls:
        wheel_url = wheel_urls[python_version]
        print(f"Installing dlib wheel for Python {python_version}")
        return run_command(f"pip install {wheel_url}", f"Installing dlib wheel")
    else:
        print(f"⚠️  No pre-compiled wheel available for Python {python_version}")
        print("Trying alternative methods...")
        
        # Try dlib-bin
        if run_command("pip install dlib-bin", "Installing dlib-bin (alternative)"):
            return True
            
        print("❌ All dlib installation methods failed")
        return False

def main():
    """Main installation process"""
    print("🚀 Starting FastAPI + Face Recognition Installation")
    print(f"Python version: {get_python_version()}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    
    # Step 1: Upgrade pip
    if not run_command("python -m pip install --upgrade pip setuptools wheel", 
                      "Upgrading pip and tools"):
        print("Failed to upgrade pip")
        return False
    
    # Step 2: Install numpy first
    if not run_command("pip install 'numpy>=1.21.0,<2.0.0'", 
                      "Installing numpy"):
        print("Failed to install numpy")
        return False
    
    # Step 3: Install dlib using pre-compiled wheel
    dlib_success = install_dlib_precompiled()
    
    # Step 4: Install opencv
    if not run_command("pip install opencv-python", "Installing opencv-python"):
        print("Failed to install opencv-python")
        return False
    
    # Step 5: Install face-recognition (only if dlib succeeded)
    face_recognition_success = False
    if dlib_success:
        face_recognition_success = run_command("pip install face-recognition", 
                                             "Installing face-recognition")
    
    # Step 6: Install FastAPI ecosystem
    fastapi_packages = [
        "fastapi==0.116.1",
        "uvicorn[standard]==0.33.0", 
        "python-multipart==0.0.20",
        "python-jose[cryptography]==3.4.0",
        "passlib[bcrypt]==1.7.4",
        "sqlalchemy==2.0.43",
        "pymysql==1.1.2",
        "pydantic==2.10.6",
        "python-dotenv==1.0.1",
        "requests==2.32.4"
    ]
    
    print("\n" + "="*60)
    print("INSTALLING FASTAPI PACKAGES")
    print("="*60)
    
    for package in fastapi_packages:
        run_command(f"pip install {package}", f"Installing {package}")
    
    # Step 7: Install additional packages
    additional_packages = [
        "pillow>=9.0.0",
        "scikit-learn>=1.0.0", 
        "scipy>=1.7.0",
        "matplotlib",
        "pandas"
    ]
    
    print("\n" + "="*60)  
    print("INSTALLING ADDITIONAL PACKAGES")
    print("="*60)
    
    for package in additional_packages:
        run_command(f"pip install {package}", f"Installing {package}")
    
    # Step 8: Final verification
    print("\n" + "="*60)
    print("INSTALLATION VERIFICATION") 
    print("="*60)
    
    verification_packages = [
        "numpy", "opencv-python", "fastapi", "uvicorn", "sqlalchemy", "pydantic"
    ]
    
    if dlib_success:
        verification_packages.append("dlib")
    if face_recognition_success:
        verification_packages.append("face-recognition")
    
    for package in verification_packages:
        run_command(f"python -c \"import {package.replace('-', '_')}; print(f'{package}: OK')\"", 
                   f"Testing {package}")
    
    print("\n" + "="*60)
    print("INSTALLATION SUMMARY")
    print("="*60)
    print(f"✅ Core packages: Installed")
    print(f"✅ FastAPI ecosystem: Installed") 
    print(f"{'✅' if dlib_success else '❌'} dlib: {'Installed' if dlib_success else 'Failed'}")
    print(f"{'✅' if face_recognition_success else '❌'} face-recognition: {'Installed' if face_recognition_success else 'Failed'}")
    
    if not dlib_success:
        print("\n⚠️  DLIB INSTALLATION FAILED")
        print("You can still use FastAPI, but face recognition features won't work.")
        print("Consider using conda: conda install -c conda-forge dlib")
    
    print("\n🎉 Installation completed!")
    
    # Show installed packages
    run_command("pip list", "Final package list")

if __name__ == "__main__":
    main()