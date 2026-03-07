import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QTransform, QFont
from PyQt6.QtCore import Qt

class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(300, 300)
        self.rotation = 45.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        transform = QTransform()
        cw = self.width() / 2.0
        ch = self.height() / 2.0
        
        transform.translate(cw, ch)
        try:
            print("trying rotation with 800")
            transform.rotate(self.rotation, Qt.Axis.YAxis, 800.0)
            print("after rotation")
        except Exception as e:
            print(f"Exception: {e}")
        transform.translate(-cw, -ch)
        
        try:
            print("trying setTransform")
            painter.setTransform(transform)
            print("after setTransform")
        except Exception as e:
            print(f"Exception: {e}")
        
        painter.setFont(QFont("Arial", 24))
        painter.drawText(100, 100, "Testing")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = TestWidget()
    w.show()
    sys.exit(app.exec())
