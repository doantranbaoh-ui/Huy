# --- imghdr_mock.py ---
"""
Mock imghdr using filetype — không cần Pillow
"""

import sys
import filetype

def detect_image_type(file_data: bytes) -> str:
    """Detect image type using filetype only"""
    try:
        guess = filetype.guess(file_data)
        if guess:
            return guess.extension
        return None
    except:
        return None

# Mock imghdr for Python 3.14+
if sys.version_info >= (3, 14):
    try:
        import imghdr
    except ImportError:
        import types
        
        mock_imghdr = types.ModuleType("imghdr")
        
        def what(file, h=None):
            try:
                if isinstance(file, str):
                    with open(file, 'rb') as f:
                        data = f.read(261)
                else:
                    data = file.read(261) if hasattr(file, 'read') else file
                return detect_image_type(data)
            except:
                return None
                
        mock_imghdr.what = what
        sys.modules['imghdr'] = mock_imghdr
        print("✅ Mock imghdr created (filetype only)")
