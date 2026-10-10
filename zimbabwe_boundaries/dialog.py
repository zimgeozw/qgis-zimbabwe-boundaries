import os

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, QgsProject, QgsSettings
from qgis.gui import QgsFileWidget, QgsProjectionSelectionWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QGridLayout,
)

from . import core
from .compat import E

KEY = 'zimbabwe_boundaries/'


class BoundariesDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Zimbabwe boundaries')
        self.setMinimumSize(1250, 500)
        s = QgsSettings()
        lay = QVBoxLayout(self)

        head = QHBoxLayout()
        logo = QLabel()
        pm = QPixmap(os.path.join(os.path.dirname(__file__), 'zimgeo_logo.png'))
        if not pm.isNull():
            logo.setPixmap(pm.scaledToHeight(40, E(Qt, 'TransformationMode', 'SmoothTransformation')))
        head.addWidget(logo)
        intro = QLabel('<b>Administrative boundaries of Zimbabwe</b><br>'
                       'Country, 10 provinces, 91 districts and 1,961 wards (2018). Add them to the map or save them as files.')
        intro.setWordWrap(True)
        head.addWidget(intro, 1)
        lay.addLayout(head)
        body = QHBoxLayout()
        body.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        lay.addLayout(body, 1)

        # levels
        g = QGroupBox('Levels')
        gl = QVBoxLayout(g)
        self.level_boxes = {}
        for lvl, info in core.LEVELS.items():
            n = info['count']
            cb = QCheckBox('%s  (%s)' % (info['title'], '{:,}'.format(n)))
            cb.setChecked(s.value(KEY + 'level%d' % lvl, lvl < 3, type=bool))
            cb.toggled.connect(self._update)
            gl.addWidget(cb)
            self.level_boxes[lvl] = cb
        self.ward_note = QLabel('Wards are the 2018 boundaries, older than the latest delimitation. Check them against current ZEC ward maps.')
        self.ward_note.setWordWrap(True)
        self.ward_note.setStyleSheet('color:#a05a00; font-size:11px')
        gl.addWidget(self.ward_note)
        left.addWidget(g)

        # provinces
        g = QGroupBox('Provinces')
        gl = QVBoxLayout(g)
        self.prov_list = QListWidget()
        self.prov_list.setMinimumHeight(260)
        self.prov_list.setMinimumWidth(210)
        for p in core.provinces():
            it = QListWidgetItem(p)
            it.setFlags(it.flags() | E(Qt, 'ItemFlag', 'ItemIsUserCheckable'))
            it.setCheckState(E(Qt, 'CheckState', 'Checked'))
            self.prov_list.addItem(it)
        self.prov_list.itemChanged.connect(self._fill_districts)
        gl.addWidget(self.prov_list)
        row = QHBoxLayout()
        for text, state in (('Select all', E(Qt, 'CheckState', 'Checked')), ('Clear', E(Qt, 'CheckState', 'Unchecked'))):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, st=state: self._set_all(self.prov_list, st))
            row.addWidget(b)
        row.addStretch(1)
        gl.addLayout(row)
        g.setToolTip('Limits levels 1, 2 and 3')
        self.prov_group = g
        filters = QHBoxLayout()
        filters.addWidget(g)

        g = QGroupBox('Districts')
        gl = QVBoxLayout(g)
        self.dist_list = QListWidget()
        self.dist_list.setMinimumHeight(260)
        self.dist_list.setMinimumWidth(290)
        gl.addWidget(self.dist_list)
        row = QHBoxLayout()
        for text, state in (('Select all', E(Qt, 'CheckState', 'Checked')), ('Clear', E(Qt, 'CheckState', 'Unchecked'))):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, st=state: self._set_all(self.dist_list, st))
            row.addWidget(b)
        row.addStretch(1)
        gl.addLayout(row)
        g.setToolTip('Limits levels 2 and 3')
        self.dist_group = g
        filters.addWidget(g)
        self._all_districts = core.districts()
        self._fill_districts()

        # coordinate system
        g = QGroupBox('Coordinate system')
        gl = QVBoxLayout(g)
        self.crs = QgsProjectionSelectionWidget()
        self.crs.setCrs(QgsCoordinateReferenceSystem(s.value(KEY + 'crs', 'EPSG:4326')))
        gl.addWidget(self.crs)
        quick = QHBoxLayout()
        for label, code in (('WGS 84', 'EPSG:4326'), ('UTM 35S', 'EPSG:32735'), ('UTM 36S', 'EPSG:32736')):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, c=code: self.crs.setCrs(QgsCoordinateReferenceSystem(c)))
            quick.addWidget(b)
        quick.addStretch(1)
        gl.addLayout(quick)
        hint = QLabel('UTM gives metres: 35S for the west, 36S for the centre and east.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#5e6b73')
        gl.addWidget(hint)
        left.addWidget(g)
        left.addStretch(1)

        # output
        g = QGroupBox('Output')
        gl = QGridLayout(g)
        self.add_map = QCheckBox('Add to the map')
        self.add_map.setChecked(s.value(KEY + 'add_map', True, type=bool))
        self.labels = QCheckBox('Show labels')
        self.labels.setChecked(s.value(KEY + 'labels', True, type=bool))
        gl.addWidget(self.add_map, 0, 0)
        gl.addWidget(self.labels, 0, 1)
        self.save = QCheckBox('Save files to a folder')
        self.save.setChecked(s.value(KEY + 'save', True, type=bool))
        self.save.toggled.connect(self._update)
        gl.addWidget(self.save, 1, 0, 1, 2)
        gl.addWidget(QLabel('Format'), 2, 0)
        self.fmt = QComboBox()
        self.fmt.addItems(list(core.FORMATS))
        self.fmt.setCurrentText(s.value(KEY + 'format', 'Shapefile (.shp)'))
        gl.addWidget(self.fmt, 2, 1)
        gl.addWidget(QLabel('Folder'), 3, 0)
        self.folder = QgsFileWidget()
        self.folder.setStorageMode(E(QgsFileWidget, 'StorageMode', 'GetDirectory'))
        self.folder.setFilePath(s.value(KEY + 'folder', os.path.expanduser('~')))
        gl.addWidget(self.folder, 3, 1)
        self.zip = QCheckBox('Pack into one zip file')
        self.zip.setChecked(s.value(KEY + 'zip', False, type=bool))
        gl.addWidget(self.zip, 4, 1)
        right.addWidget(g)
        src = QLabel(core.ATTRIBUTION)
        src.setWordWrap(True)
        src.setStyleSheet('color:#5e6b73; font-size:11px')
        right.addWidget(src)
        right.addStretch(1)

        body.addLayout(left, 4)
        body.addLayout(filters, 6)
        body.addLayout(right, 4)

        bb = QDialogButtonBox(E(QDialogButtonBox, 'StandardButton', 'Cancel'))
        self.go = bb.addButton('Get boundaries', E(QDialogButtonBox, 'ButtonRole', 'AcceptRole'))
        bb.accepted.connect(self.run)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._update()
        self.adjustSize()
        self.resize(1340, max(self.sizeHint().height() + 60, 540))

    def _set_all(self, widget, state):
        widget.blockSignals(True)
        for i in range(widget.count()):
            widget.item(i).setCheckState(state)
        widget.blockSignals(False)
        if widget is self.prov_list:
            self._fill_districts()

    def _checked(self, widget):
        return [widget.item(i).data(E(Qt, 'ItemDataRole', 'UserRole')) or widget.item(i).text()
                for i in range(widget.count()) if widget.item(i).checkState() == E(Qt, 'CheckState', 'Checked')]

    def _fill_districts(self, *_):
        provs = set(self._checked(self.prov_list))
        was_unchecked = {self.dist_list.item(i).data(E(Qt, 'ItemDataRole', 'UserRole')) for i in range(self.dist_list.count())
                         if self.dist_list.item(i).checkState() != E(Qt, 'CheckState', 'Checked')}
        self.dist_list.clear()
        for d, p in self._all_districts:
            if p in provs:
                it = QListWidgetItem('%s  (%s)' % (d, p))
                it.setData(E(Qt, 'ItemDataRole', 'UserRole'), d)
                it.setFlags(it.flags() | E(Qt, 'ItemFlag', 'ItemIsUserCheckable'))
                it.setCheckState(E(Qt, 'CheckState', 'Unchecked') if d in was_unchecked else E(Qt, 'CheckState', 'Checked'))
                self.dist_list.addItem(it)

    def _update(self):
        lv = [l for l, cb in self.level_boxes.items() if cb.isChecked()]
        self.prov_group.setEnabled(any(l > 0 for l in lv))
        self.dist_group.setEnabled(any(l in (2, 3) for l in lv))
        self.ward_note.setVisible(3 in lv)
        for w in (self.fmt, self.folder, self.zip):
            w.setEnabled(self.save.isChecked())
        self.go.setEnabled(bool(lv))

    def selected_provinces(self):
        chosen = self._checked(self.prov_list)
        return None if len(chosen) == self.prov_list.count() else chosen

    def selected_districts(self):
        chosen = self._checked(self.dist_list)
        return None if len(chosen) == self.dist_list.count() else chosen

    def _remember(self):
        s = QgsSettings()
        for l, cb in self.level_boxes.items():
            s.setValue(KEY + 'level%d' % l, cb.isChecked())
        s.setValue(KEY + 'crs', self.crs.crs().authid())
        for k, w in (('add_map', self.add_map), ('labels', self.labels), ('save', self.save), ('zip', self.zip)):
            s.setValue(KEY + k, w.isChecked())
        s.setValue(KEY + 'format', self.fmt.currentText())
        s.setValue(KEY + 'folder', self.folder.filePath())

    def run(self):
        levels = [l for l, cb in self.level_boxes.items() if cb.isChecked()]
        provs = self.selected_provinces()
        dists = self.selected_districts()
        if provs is not None and not provs and any(l > 0 for l in levels):
            QMessageBox.warning(self, 'Zimbabwe boundaries', 'Select at least one province.')
            return
        if dists is not None and not dists and any(l > 1 for l in levels):
            QMessageBox.warning(self, 'Zimbabwe boundaries', 'Select at least one district.')
            return
        if not self.add_map.isChecked() and not self.save.isChecked():
            QMessageBox.warning(self, 'Zimbabwe boundaries', 'Choose to add the boundaries to the map, save them, or both.')
            return
        folder = self.folder.filePath().strip()
        if self.save.isChecked() and not folder:
            QMessageBox.warning(self, 'Zimbabwe boundaries', 'Choose a folder to save the files in.')
            return
        self._remember()
        QApplication.setOverrideCursor(E(Qt, 'CursorShape', 'WaitCursor'))
        try:
            layers = [core.make_layer(l, provinces=provs, districts=dists, crs=self.crs.crs()) for l in levels]
            files = []
            if self.save.isChecked():
                driver = core.FORMATS[self.fmt.currentText()][0]
                zip_name = None
                if self.zip.isChecked():
                    names = dists if (dists is not None and any(l > 1 for l in levels)) else provs
                    tag = '' if names is None else '_' + '_'.join(p.lower().replace(' ', '') for p in names)[:40]
                    zip_name = 'zimbabwe_boundaries%s_%s.zip' % (tag, driver.split()[-1].lower())
                files = core.save_layers(layers, folder, driver, zip_name)
            if self.add_map.isChecked():
                loose = [f for f in files if not f.endswith('.zip')]
                to_add = core.add_saved_to_map(loose, levels) if loose else [(l.customProperty('zwe_level'), l) for l in layers]
                if len(to_add) < len(levels):  # e.g. zipped output: fall back to temporary layers
                    to_add = [(int(l.customProperty('zwe_level')), l) for l in layers]
                self._add_to_map(to_add)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, 'Zimbabwe boundaries', str(e))
            return
        QApplication.restoreOverrideCursor()
        msg = '%d layer%s ready' % (len(levels), '' if len(levels) == 1 else 's')
        if files:
            msg += '; saved to %s' % (files[0] if len(files) == 1 else folder)
        self.iface.messageBar().pushMessage('Zimbabwe boundaries', msg, E(Qgis, 'MessageLevel', 'Success'), 8)
        self.accept()

    def _add_to_map(self, items):
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        group = root.findGroup('Zimbabwe boundaries') or root.insertGroup(0, 'Zimbabwe boundaries')
        # districts at the bottom, country outline on top
        for level, lyr in sorted(items, key=lambda x: -int(x[0])):
            core.style_layer(lyr, int(level), labels=self.labels.isChecked())
            proj.addMapLayer(lyr, False)
            group.insertChildNode(0, QgsLayerTreeLayer(lyr))
        if items:
            canvas = self.iface.mapCanvas()
            from qgis.core import QgsCoordinateTransform
            lyr = items[0][1]
            ext = QgsCoordinateTransform(lyr.crs(), canvas.mapSettings().destinationCrs(), proj).transformBoundingBox(lyr.extent())
            ext.scale(1.05)
            canvas.setExtent(ext)
            canvas.refresh()
