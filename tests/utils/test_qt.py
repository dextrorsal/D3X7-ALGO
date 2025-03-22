from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
import sys

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setGeometry(100, 100, 200, 200)
    window.setWindowTitle("Test Window")
    
    button = QPushButton("Test Button", window)
    button.move(50, 50)
    
    window.show()
    sys.exit(app.exec()) 