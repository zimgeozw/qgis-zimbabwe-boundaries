import os

from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction  # Qt 6 (QGIS 4)
except ImportError:
    from qgis.PyQt.QtWidgets import QAction  # Qt 5 (QGIS 3)

from .compat import exec_dialog


class ZimbabweBoundariesPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))
        self.action = QAction(icon, 'Zimbabwe boundaries (levels 0 to 3)', self.iface.mainWindow())
        self.action.setToolTip('Add or save Zimbabwe country, province and district boundaries')
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu('&Zimbabwe boundaries', self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginVectorMenu('&Zimbabwe boundaries', self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        from .dialog import BoundariesDialog
        exec_dialog(BoundariesDialog(self.iface, self.iface.mainWindow()))
