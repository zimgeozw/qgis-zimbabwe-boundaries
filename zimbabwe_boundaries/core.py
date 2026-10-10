"""Zimbabwe administrative boundaries: load, filter, reproject, style and save.

Works without the dialog, so it can also be used from the QGIS Python console:

    from zimbabwe_boundaries import core
    lyr = core.make_layer(2, provinces=['Manicaland'])
    core.save_layers([lyr], '/path/to/folder', 'ESRI Shapefile')
"""
import os
import zipfile

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsFeature, QgsFeatureRequest, QgsFillSymbol, QgsPalLayerSettings, QgsProject,
    QgsSingleSymbolRenderer, QgsTextBufferSettings, QgsTextFormat, QgsVectorFileWriter, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont

from .compat import E, is_zero

DATA = os.path.join(os.path.dirname(__file__), 'data', 'zimbabwe_boundaries.gpkg')

LEVELS = {
    0: {'table': 'zwe_level0_country', 'title': 'Level 0: country', 'layer': 'Zimbabwe level 0 country',
        'file': 'zwe_level0_country', 'label': 'country', 'count': 1},
    1: {'table': 'zwe_level1_provinces', 'title': 'Level 1: provinces', 'layer': 'Zimbabwe level 1 provinces',
        'file': 'zwe_level1_provinces', 'label': 'province', 'count': 10},
    2: {'table': 'zwe_level2_districts', 'title': 'Level 2: districts', 'layer': 'Zimbabwe level 2 districts',
        'file': 'zwe_level2_districts', 'label': 'district', 'count': 91},
    3: {'table': 'zwe_level3_wards_2018', 'title': 'Level 3: wards, 2018 (old)',
        'layer': 'Zimbabwe level 3 wards (2018, old)', 'file': 'zwe_level3_wards_2018', 'label': 'ward', 'count': 1961},
}

FORMATS = {
    'Shapefile (.shp)': ('ESRI Shapefile', '.shp'),
    'GeoPackage (.gpkg)': ('GPKG', '.gpkg'),
    'GeoJSON (.geojson)': ('GeoJSON', '.geojson'),
    'KML for Google Earth (.kml)': ('KML', '.kml'),
}

ATTRIBUTION = ('Boundaries: Zimbabwe National Statistics Agency (ZIMSTAT) and OCHA ROSEA, '
               'Common Operational Dataset of administrative boundaries (COD-AB), valid from 11 September 2018, '
               'published on the Humanitarian Data Exchange (data.humdata.org). Licence: CC BY-IGO.')
WARD_NOTE = ('The wards are the 2018 ward boundaries. They are older than the latest ward delimitation, '
             'so check them against current Zimbabwe Electoral Commission ward maps before using them for '
             'electoral or ward-level planning work.')

STYLE = {  # outline colour, width (mm), label size (pt)
    0: ('#0f3d57', 0.8, 11),
    1: ('#1b78a8', 0.5, 9),
    2: ('#6b7a83', 0.3, 7),
    3: ('#a3b1b9', 0.15, 6),
}


def _quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def source_layer(level):
    uri = '%s|layername=%s' % (DATA, LEVELS[level]['table'])
    lyr = QgsVectorLayer(uri, LEVELS[level]['layer'], 'ogr')
    if not lyr.isValid():
        raise RuntimeError('Could not open the boundary data in %s' % DATA)
    return lyr


def provinces():
    return sorted(f['province'] for f in source_layer(1).getFeatures())


def districts(province_names=None):
    out = []
    for f in source_layer(2).getFeatures():
        if not province_names or f['province'] in province_names:
            out.append((f['district'], f['province']))
    return sorted(out)


def make_layer(level, provinces=None, districts=None, crs=None):
    """Return a temporary (memory) layer for one level.

    provinces and districts are optional lists of names that limit levels 1 and 2.
    crs is a QgsCoordinateReferenceSystem; the data is stored in WGS 84 (EPSG:4326).
    """
    src = source_layer(level)
    clauses = []
    if provinces and level in (1, 2, 3):
        clauses.append('"province" IN (%s)' % ', '.join(_quote(p) for p in provinces))
    if districts and level in (2, 3):
        clauses.append('"district" IN (%s)' % ', '.join(_quote(d) for d in districts))
    req = QgsFeatureRequest()
    if clauses:
        req.setFilterExpression(' AND '.join(clauses))
    crs = crs if (crs is not None and crs.isValid()) else src.crs()
    if crs != src.crs():
        req.setDestinationCrs(crs, QgsProject.instance().transformContext())
    # copy into a temporary layer (done by hand so it works on every QGIS version)
    mem = QgsVectorLayer('MultiPolygon?crs=%s' % crs.authid() if crs.authid() else 'MultiPolygon',
                         LEVELS[level]['layer'], 'memory')
    if not crs.authid():
        mem.setCrs(crs)
    fields = [f for f in src.fields() if f.name() != 'fid']  # fid is the GeoPackage row id
    mem.dataProvider().addAttributes(fields)
    mem.updateFields()
    names = [f.name() for f in fields]
    feats = []
    for f in src.getFeatures(req):
        nf = QgsFeature(mem.fields())
        nf.setGeometry(f.geometry())
        nf.setAttributes([f[n] for n in names])
        feats.append(nf)
    mem.dataProvider().addFeatures(feats)
    mem.updateExtents()
    mem.setName(LEVELS[level]['layer'])
    mem.setCrs(crs)
    md = mem.metadata()
    md.setRights([ATTRIBUTION] + ([WARD_NOTE] if level == 3 else []))
    md.setLicenses(['CC BY 3.0 IGO'])
    md.setTitle(LEVELS[level]['layer'])
    mem.setMetadata(md)
    mem.setCustomProperty('zwe_level', level)
    return mem


def style_layer(layer, level, labels=True):
    colour, width, size = STYLE[level]
    sym = QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_color': colour, 'outline_width': str(width),
                                      'outline_width_unit': 'MM', 'style': 'no'})
    layer.setRenderer(QgsSingleSymbolRenderer(sym))
    if labels:
        s = QgsPalLayerSettings()
        s.fieldName = LEVELS[level]['label']
        fmt = QgsTextFormat()
        f = QFont('Arial')
        f.setBold(level < 2)
        fmt.setFont(f)
        fmt.setSize(size)
        fmt.setColor(QColor(colour if level < 2 else '#3d4a52'))
        if level == 3:
            s.scaleVisibility = True
            s.minimumScale = 300000  # ward numbers only when zoomed in
            s.maximumScale = 0
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(0.8)
        buf.setColor(QColor('white'))
        fmt.setBuffer(buf)
        s.setFormat(fmt)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
        layer.setLabelsEnabled(level > 0)
    layer.triggerRepaint()
    return layer


def _write(layer, path, ctx, opts):
    """Save a layer with whichever writer this QGIS version has (V3: 3.20+, V2: 3.10+, older)."""
    W = QgsVectorFileWriter
    if hasattr(W, 'writeAsVectorFormatV3'):
        res = W.writeAsVectorFormatV3(layer, path, ctx, opts)
    elif hasattr(W, 'writeAsVectorFormatV2'):
        res = W.writeAsVectorFormatV2(layer, path, ctx, opts)
    else:
        res = W.writeAsVectorFormat(layer, path, opts)
    if not isinstance(res, tuple):
        res = (res, '')
    return res[0], (res[1] if len(res) > 1 else '')


def save_layers(layers, folder, driver, zip_name=None):
    """Save layers to folder in the given OGR driver. Returns the list of files written.

    GeoPackage puts all layers in one file. If zip_name is given, everything written is
    also packed into folder/zip_name and the loose files are removed.
    """
    os.makedirs(folder, exist_ok=True)
    ext = {v[0]: v[1] for v in FORMATS.values()}[driver]
    ctx = QgsProject.instance().transformContext()
    written = []
    gpkg_path = os.path.join(folder, 'zimbabwe_boundaries.gpkg')
    for i, lyr in enumerate(layers):
        level = int(lyr.customProperty('zwe_level', 0))
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = driver
        opts.fileEncoding = 'UTF-8'
        if driver == 'GPKG':
            path = gpkg_path
            opts.layerName = LEVELS[level]['file']
            opts.actionOnExistingFile = E(QgsVectorFileWriter, 'ActionOnExistingFile',
                                          'CreateOrOverwriteLayer' if i > 0 and os.path.exists(path) else 'CreateOrOverwriteFile')
        else:
            path = os.path.join(folder, LEVELS[level]['file'] + ext)
            if driver == 'KML':
                opts.datasourceOptions = ['NameField=' + LEVELS[level]['label']]
        err, msg = _write(lyr, path, ctx, opts)
        if not is_zero(err):
            raise RuntimeError('Could not save %s: %s' % (lyr.name(), msg))
        if driver == 'ESRI Shapefile':
            base = os.path.splitext(path)[0]
            for e in ('.shp', '.shx', '.dbf', '.prj', '.cpg'):
                if os.path.exists(base + e) and base + e not in written:
                    written.append(base + e)
        elif path not in written:
            written.append(path)
    notice = os.path.join(folder, 'zimbabwe_boundaries_SOURCE.txt')
    with open(notice, 'w', encoding='utf-8') as fh:
        fh.write(ATTRIBUTION + '\n' + (WARD_NOTE + '\n' if any(int(l.customProperty('zwe_level', 0)) == 3 for l in layers) else '') +
                 'Prepared with the Zimbabwe Boundaries QGIS plugin by Zimgeo (www.zimgeo.co.zw).\n')
    written.append(notice)
    if zip_name:
        zpath = os.path.join(folder, zip_name)
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in written:
                z.write(p, os.path.basename(p))
        for p in written:
            os.remove(p)
        return [zpath]
    return written


def add_saved_to_map(files, levels):
    """Add saved files to the project (so the project keeps working after QGIS restarts)."""
    added = []
    for level in levels:
        name = LEVELS[level]['file']
        for p in files:
            base = os.path.basename(p)
            if p.endswith('.gpkg'):
                lyr = QgsVectorLayer('%s|layername=%s' % (p, name), LEVELS[level]['layer'], 'ogr')
            elif os.path.splitext(base)[0] == name and os.path.splitext(base)[1] in ('.shp', '.geojson', '.kml'):
                lyr = QgsVectorLayer(p, LEVELS[level]['layer'], 'ogr')
            else:
                continue
            if lyr.isValid():
                added.append((level, lyr))
            break
    return added
