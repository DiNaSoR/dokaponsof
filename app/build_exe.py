import os
import sys
import shutil
import PyInstaller.__main__

# Add the parent directory to Python path so it can find the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def build_exe():
    """Build standalone executable using PyInstaller"""
    
    # Get absolute paths
    app_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(app_dir, "resources")
    icon_path = os.path.join(resources_dir, "icon.ico")
    main_script = os.path.join(app_dir, "main.py")
    
    # Clean build and dist directories
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # PyInstaller command line arguments
    args = [
        main_script,  # Use the full path to main.py
        '--name', 'DokaponSoFTools',  # Separate name argument
        '--onefile',  # Create single executable
        '--windowed',  # Don't show console window
        '--icon', icon_path,  # Separate icon argument
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace output directory without confirmation
        
        # Add data files with explicit file specifications
        '--add-data', f'{os.path.join(resources_dir, "bgm.mp3")}{os.pathsep}resources',
        '--add-data', f'{os.path.join(resources_dir, "icon.ico")}{os.pathsep}resources',
        
        # Hidden imports
        '--hidden-import', 'PIL',
        '--hidden-import', 'numpy',
        '--hidden-import', 'PyQt6.QtMultimedia',
        
        # Specify output directory
        '--distpath', 'build'
    ]
    
    try:
        print("Starting build process...")
        print(f"Building from: {main_script}")
        print(f"Resources dir: {resources_dir}")
        
        PyInstaller.__main__.run(args)
        
        print("\nBuild completed successfully!")
        print(f"Executable created at: {os.path.join('build', 'DokaponSoFTools.exe')}")
        
    except Exception as e:
        print(f"\nError during build: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe() 