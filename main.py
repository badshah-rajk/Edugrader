"""
EduGrader — Student Answer Copy OCR & Annotation System
Entry point
"""
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from app.app import EduGraderApp

if __name__ == "__main__":
    app = EduGraderApp()
    app.run()
