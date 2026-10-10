"""Small helpers so the plugin runs on old QGIS 3 (PyQt5) and on QGIS 4 (PyQt6)."""


def E(owner, scope, name):
    """Return owner.scope.name (scoped enums, PyQt6 / newer QGIS) or owner.name (older)."""
    scoped = getattr(owner, scope, None)
    if scoped is not None and hasattr(scoped, name):
        return getattr(scoped, name)
    return getattr(owner, name)


def is_zero(value):
    """True for an enum or int equal to 0 (e.g. QgsVectorFileWriter NoError) in PyQt5 and PyQt6."""
    try:
        return int(value) == 0
    except (TypeError, ValueError):
        return getattr(value, 'value', None) == 0


def exec_dialog(dlg):
    return dlg.exec() if hasattr(dlg, 'exec') else dlg.exec_()
